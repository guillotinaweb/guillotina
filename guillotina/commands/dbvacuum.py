from guillotina.commands import Command
from guillotina.component import get_utility
from guillotina.db import ROOT_ID
from guillotina.db import TRASHED_ID
from guillotina.db.storages.sql import SQL
from guillotina.interfaces import IApplication
from guillotina.interfaces import IDatabase

import asyncio
import logging


logger = logging.getLogger('guillotina')

BATCH_SIZE = 1000
NUM_CONNECTIONS = 5

GET_OBJECTS = SQL('''
SELECT zoid, resource, parent_id, of
FROM {table}
ORDER BY zoid
LIMIT $1
OFFSET $2
''')
DELETE_BLOBS = SQL(
    "DELETE FROM {table} WHERE zoid = ANY($1);", 'blobs')
DELETE_OBJECTS = SQL("""
DELETE FROM {table}
WHERE zoid = ANY($1);
""")


class DBVacuum:
    remove_batch_size = 100

    def __init__(self, request, options, db):
        self.request = request
        self.options = options
        self.db = db
        self.objects = {}
        self.remove_batch = []
        self.removed = []
        self.total = 0
        self.run_total = 0
        self.tm = self.db.get_transaction_manager()
        self.storage = self.tm._storage

    async def get_batch_batch(self, conns, offset=0):
        funcs = []
        for conn in conns:
            funcs.append(conn.fetch(GET_OBJECTS.render(), BATCH_SIZE, offset))
            offset += BATCH_SIZE

        results = []
        for result in await asyncio.gather(*funcs):
            results.extend(result)
        return results

    async def gather_data(self):
        offset = 0
        conns = []
        for _ in range(5):
            conns.append(await self.storage.open())

        results = await self.get_batch_batch(conns)
        while len(results) > 0:
            for item in results:
                self.objects[item['zoid']] = {
                    'resource': item['resource'],
                    'parent_id': item['parent_id'],
                    'of': item['of']
                }
            offset += len(results)
            print(f'Got page of {len(results)}/{len(self.objects)} objects')
            results = await self.get_batch_batch(conns, offset)

        for conn in conns:
            await self.storage.close(conn)

    async def process_batch(self):
        if not self.options.dry_run:
            await self.conn.execute(DELETE_BLOBS.render(), self.remove_batch)
            await self.conn.execute(DELETE_OBJECTS.render(), self.remove_batch)
        self.removed.extend(self.remove_batch)
        self.total += len(self.remove_batch)
        self.run_total += len(self.remove_batch)
        print(f'Vacuumed ({len(self.remove_batch)}/{self.total}): {self.remove_batch}')
        self.remove_batch = []

    async def vacuum(self):
        self.conn = await self.storage.open()
        await self.gather_data()

        while await self._vacuum() > 0:
            # vacuum until we're done...
            for zoid in self.removed:
                del self.objects[zoid]
            self.removed = []
            self.run_total = 0

    async def _vacuum(self):
        for zoid, data in self.objects.items():
            if zoid in (TRASHED_ID, ROOT_ID):
                continue

            if data['resource']:
                if (not data['parent_id'] or data['parent_id'] == TRASHED_ID or
                        data['parent_id'] not in self.objects):
                    self.remove_batch.append(zoid)
            else:
                if data['parent_id'] == TRASHED_ID or data['of'] not in self.objects:
                    self.remove_batch.append(zoid)

            if len(self.remove_batch) > self.remove_batch_size:
                await self.process_batch()

        if len(self.remove_batch) > 0:
            await self.process_batch()

        return self.run_total

class VacuumCommand(Command):
    description = '''
'''

    def get_parser(self):
        parser = super(VacuumCommand, self).get_parser()
        parser.add_argument('--dry-run', action='store_true')
        return parser

    async def migrate(self, arguments, db):
        vacuum = DBVacuum(arguments, db)
        await vacuum.vacuum()

    async def run(self, arguments, settings, app):
        root = get_utility(IApplication, name='root')
        for _id, db in root:
            if IDatabase.providedBy(db):
                vacuum = DBVacuum(self.request, arguments, db)
                await vacuum.vacuum()
