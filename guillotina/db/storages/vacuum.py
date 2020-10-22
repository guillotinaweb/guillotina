from guillotina import configure
from guillotina.const import TRASHED_ID
from guillotina.db.interfaces import IPostgresStorage
from guillotina.db.interfaces import IVacuumProvider
from guillotina.db.storages.utils import register_sql

import asyncio
import asyncpg.exceptions
import logging


logger = logging.getLogger("guillotina")


register_sql(
    "DELETE_TRASHED_OBJECTS",
    f"""
DELETE FROM {{table_name}}
WHERE zoid = ANY($1)
AND parent_id = '{TRASHED_ID}';
""",
)

register_sql(
    "GET_BATCH_OF_TRASHED_OBJECTS",
    f"""
SELECT zoid from {{table_name}} where parent_id = '{TRASHED_ID}'
LIMIT $1;
""",
)

register_sql(
    "TRASH_BATCH",
    f"""
WITH rows AS (
    UPDATE
        {{table_name}} t1
    SET
        parent_id = '{TRASHED_ID}'
    FROM (
            SELECT zoid
            FROM {{table_name}}
            WHERE parent_id = ANY($1)
            LIMIT $2
        ) as t2
    WHERE
        t1.zoid = t2.zoid
    RETURNING 1
)
SELECT count(*) FROM rows;
""",
)

# CR allows limit directly in update clause
register_sql(
    "CR_TRASH_BATCH",
    f"""
WITH rows AS (
    UPDATE
        {{table_name}}
    SET
        parent_id = '{TRASHED_ID}'
    WHERE
        parent_id = ANY($1)
    LIMIT $2
    RETURNING 1
)
SELECT count(*) FROM rows;
""",
)


@configure.adapter(for_=IPostgresStorage, provides=IVacuumProvider)
class PGVacuum:

    _trash_batch_name = "TRASH_BATCH"
    _pause = 0.1

    def __init__(self, storage):
        self._storage = storage
        self._trashed = 0
        self._deleted = 0

    def status(self, terminate="\r", end=""):
        print(f"trashed: {self._trashed}, deleted: {self._deleted}{terminate}", end=end)

    async def __call__(self):
        """
        - work with batches of trashed objects.
        - trash all children
        - do not delete object until all children have been reassigned as trashed
        """
        storage = self._storage
        sql = self._storage._sql
        table_name = storage._objects_table_name
        async with storage.pool.acquire() as conn:
            while True:
                batch = await conn.fetch(sql.get("GET_BATCH_OF_TRASHED_OBJECTS", table_name), 20)
                if len(batch) == 0:
                    break

                await asyncio.sleep(self._pause)
                updated = 1
                while updated > 0:
                    try:
                        result = await conn.fetch(
                            sql.get(self._trash_batch_name, table_name), [r["zoid"] for r in batch], 100
                        )
                        await asyncio.sleep(self._pause)
                        updated = result[0]["count"]
                        self._trashed += updated
                        self.status()
                    except asyncpg.exceptions.UniqueViolationError:  # pragma: no cover
                        logger.warning(
                            "Unique constraint error vacuuming. This should not happen.", exc_info=True
                        )
                        updated = 0

                await asyncio.sleep(self._pause)
                await conn.execute(sql.get("DELETE_TRASHED_OBJECTS", table_name), [r["zoid"] for r in batch])
                self._deleted += len(batch)
                self.status()
        self.status("", "\n")
