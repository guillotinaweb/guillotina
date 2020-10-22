from copy import deepcopy
from guillotina import configure
from guillotina.component import get_utility
from guillotina.db.interfaces import IDatabaseManager
from guillotina.db.storages.dummy import DummyFileStorage
from guillotina.db.storages.dummy import DummyStorage
from guillotina.db.storages.pg import PostgresqlStorage
from guillotina.db.transaction_manager import TransactionManager
from guillotina.event import notify
from guillotina.events import DatabaseInitializedEvent
from guillotina.factory.content import Database
from guillotina.interfaces import IApplication
from guillotina.interfaces import IDatabase
from guillotina.interfaces import IDatabaseConfigurationFactory
from guillotina.utils import apply_coroutine
from guillotina.utils import resolve_dotted_name
from typing import List

import asyncpg
import string


def _get_connection_options(dbconfig):
    connection_options = {}
    if "ssl" in dbconfig:
        import ssl

        ssl_config = dbconfig["ssl"]
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        ssl_context.load_verify_locations(ssl_config["ca"])
        ssl_context.load_cert_chain(ssl_config["cert"], keyfile=ssl_config["key"])
        connection_options["ssl"] = ssl_context
    for key in (
        "statement_cache_size",
        "max_cached_statement_lifetime",
        "max_cacheable_statement_size",
        "command_timeout",
        "server_settings",
    ):
        if key in dbconfig:
            connection_options[key] = dbconfig[key]
    return connection_options


def _convert_dsn(obj):
    txt = "{scheme}://{user}:{password}@{host}:{port}"
    if "dbname" in obj:
        txt += "/{dbname}"
    return txt.format(**obj)


async def _PGConfigurationFactory(key, dbconfig, loop=None, storage_factory=PostgresqlStorage):
    if isinstance(dbconfig["dsn"], str):
        dsn = dbconfig["dsn"]
    else:
        dsn = _convert_dsn(dbconfig["dsn"])

    partition_object = None
    if "partition" in dbconfig:
        partition_object = resolve_dotted_name(dbconfig["partition"])

    dbconfig.update(
        {
            "dsn": dsn,
            "name": key,
            "partition": partition_object,
            "pool_size": int(dbconfig.get("pool_size", 13)),
        }
    )

    connection_options = _get_connection_options(dbconfig)

    aps = storage_factory(**dbconfig)
    if loop is not None:
        await aps.initialize(loop=loop, **connection_options)
    else:
        await aps.initialize(**connection_options)

    if "transaction_manager" in dbconfig:
        transaction_manager = resolve_dotted_name(dbconfig["transaction_manager"])
    else:
        transaction_manager = TransactionManager
    db = Database(key, aps, transaction_manager)
    await db.initialize()
    return db


@configure.utility(provides=IDatabaseConfigurationFactory, name="postgresql")
async def PGDatabaseConfigurationFactory(key, dbconfig, loop=None):
    return await _PGConfigurationFactory(key, dbconfig, loop=loop)


@configure.utility(provides=IDatabaseConfigurationFactory, name="DUMMY")
async def DummyDatabaseConfigurationFactory(key, dbconfig, loop=None):
    dss = DummyStorage()
    db = Database(key, dss)
    await db.initialize()
    return db


@configure.utility(provides=IDatabaseConfigurationFactory, name="DUMMY_FILE")
async def DummyFileDatabaseConfigurationFactory(key, dbconfig, loop=None):
    dss = DummyFileStorage(dbconfig.get("filename", "g.db"))
    db = Database(key, dss)
    await db.initialize()
    return db


CREATE_DB = """CREATE DATABASE "{}";"""
DELETE_DB = """DROP DATABASE "{}";"""


def _safe_db_name(name):
    return "".join([l for l in name if l in string.digits + string.ascii_lowercase + "-_"])


@configure.adapter(for_=IApplication, provides=IDatabaseManager, name="postgresql")  # noqa: N801
class PostgresqlDatabaseManager:
    def __init__(self, app: IApplication, storage_config: dict) -> None:
        self.app = app
        self.config = storage_config

    def get_dsn(self, name: str = None) -> str:
        if isinstance(self.config["dsn"], str):
            dsn = self.config["dsn"]
        else:
            if "dbname" in self.config["dsn"]:
                del self.config["dsn"]["dbname"]
            dsn = _convert_dsn(self.config["dsn"])
        if name is not None:
            params = None
            if "?" in dsn:
                dsn, _, params = dsn.partition("?")
            dsn = dsn.strip("/") + "/" + name
            if params is not None:
                dsn += "?" + params
        return dsn

    async def get_connection(self, name: str = None) -> asyncpg.connection.Connection:
        connection_options = _get_connection_options(self.config)
        for key in ("max_inactive_connection_lifetime", "max_queries"):
            # these are not valid for raw connections
            if key in connection_options:
                del connection_options[key]
        dsn = self.get_dsn(name)
        return await asyncpg.connect(dsn=dsn, **connection_options)

    async def get_names(self) -> list:
        conn = await self.get_connection()
        try:
            result = await conn.fetch(
                """SELECT datname FROM pg_database
WHERE datistemplate = false;"""
            )
            return [item["datname"] for item in result]
        finally:
            await conn.close()

    async def create(self, name: str) -> bool:
        conn = await self.get_connection()
        try:
            await conn.execute(CREATE_DB.format(_safe_db_name(name)))
            return True
        finally:
            await conn.close()

    async def delete(self, name: str) -> bool:
        if name in self.app:
            await self.app[name].finalize()
            del self.app[name]

        conn = await self.get_connection()
        try:
            await conn.execute(DELETE_DB.format(_safe_db_name(name)))
            return True
        finally:
            await conn.close()

    async def get_database(self, name: str) -> IDatabase:
        if name not in self.app:
            config = deepcopy(self.config)
            config["dsn"] = self.get_dsn(name)
            factory = get_utility(IDatabaseConfigurationFactory, name=config["storage"])
            self.app[name] = await apply_coroutine(factory, name, config)
            await notify(DatabaseInitializedEvent(self.app[name]))

        return self.app[name]

    async def _check_exists(self, conn):
        """
        for pg, a conn is enough to check
        """
        return True

    async def exists(self, name: str) -> bool:
        conn = None
        try:
            conn = await self.get_connection(name)
            return await self._check_exists(conn)
        except asyncpg.exceptions.InvalidCatalogNameError:
            return False
        finally:
            if conn is not None:
                await conn.close()


DUMMY_DBS = {"guillotina": None}


@configure.adapter(for_=IApplication, provides=IDatabaseManager, name="DUMMY")  # noqa: N801
class DummyDatabaseManager:
    def __init__(self, app: IApplication, storage_config: dict) -> None:
        self.app = app
        self.config = storage_config

    async def get_names(self) -> List[str]:
        return list(DUMMY_DBS.keys())

    async def exists(self, name: str) -> bool:
        return name in DUMMY_DBS

    async def create(self, name: str) -> bool:
        DUMMY_DBS[name] = None
        return True

    async def delete(self, name: str) -> bool:
        del DUMMY_DBS[name]
        return True

    async def get_database(self, name: str) -> IDatabase:
        if name not in self.app:
            config = deepcopy(self.config)
            factory = get_utility(IDatabaseConfigurationFactory, name=config["storage"])
            self.app[name] = await apply_coroutine(factory, name, config)
            await notify(DatabaseInitializedEvent(self.app[name]))

        return self.app[name]
