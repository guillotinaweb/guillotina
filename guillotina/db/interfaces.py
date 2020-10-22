from guillotina.db.orm.interfaces import IBaseObject
from guillotina.interfaces import ICatalogDataAdapter
from guillotina.interfaces import IDatabase
from zope.interface import Attribute
from zope.interface import Interface
from zope.interface import interfaces

import asyncio
import typing


class IPartition(Interface):
    """Get the partition of the object"""


class IWriter(Interface):
    """Serializes the object for DB storage"""


class ITransaction(Interface):
    _db_conn = Attribute("")
    _query_count_end = Attribute("")
    user = Attribute("")
    status = Attribute("")
    storage = Attribute("")
    manager = Attribute("")
    lock = Attribute("")
    _cache = Attribute("")

    def initialize(read_only: bool):
        """
        Reset transient information to enable reusage of the transaction
        """

    async def add_after_commit_hook(hook, *real_args, args=None, kws=None, **kwargs):
        """
        Add hook to be called after transaction commit
        """

    async def add_before_commit_hook(hook, *real_args, args=None, kws=None, **kwargs):
        """
        Add hook to be called before txn commit
        """

    async def commit():
        """
        Commit the transaction
        """

    async def abort():
        """
        Abort the transaction
        """

    def get_query_count() -> int:
        """
        Get number of queries tranaction ran
        """

    async def tpc_begin():
        """
        """

    async def get(oid: str) -> typing.Optional[IBaseObject]:
        """
        Get oid object
        """

    async def contains(oid: str, key: str) -> bool:
        """
        Does an object container another
        """

    def register(obj: IBaseObject, new_oid: typing.Optional[str] = None):
        """
        register object with transaction to be written
        """

    async def get_child(parent: IBaseObject, key: str) -> typing.Optional[IBaseObject]:
        """
        Get child of object
        """

    async def get_children(parent: IBaseObject, keys: typing.List[str]) -> typing.AsyncIterator[IBaseObject]:
        """
        Get children of object
        """

    def delete(obj: IBaseObject):
        """
        delete object
        """

    async def len(oid: str) -> bool:
        """
        Get size of children for object
        """

    async def keys(oid: str) -> typing.List[str]:
        """
        Get all keys for object
        """

    async def items(content: IBaseObject) -> typing.AsyncIterator[typing.Tuple[str, IBaseObject]]:
        """
        Get items in content
        """

    async def get_connection() -> typing.Any:
        """
        Get current connection object
        """


class ITransactionManager(Interface):
    db_id: str
    storage: "IStorage"
    lock: asyncio.Lock

    async def commit(*, txn: typing.Optional[ITransaction] = None):
        """
        Commit txn
        """

    async def abort(*, txn: typing.Optional[ITransaction] = None):
        """
        abort txn
        """

    async def begin(read_only: bool = False) -> ITransaction:
        """
        Begin new transaction
        """

    async def get_root(txn: typing.Optional[ITransaction]) -> IBaseObject:
        """
        Begin new transaction
        """

    def transaction(**kwargs):
        """
        Return new transaction context manager
        """

    def __enter__() -> "ITransactionManager":
        """
        set task var
        """

    def __exit__(*args):
        """
        contextvars already tears down to previous value, do not set to None here!
        """

    async def __aenter__() -> "ITransactionManager":
        """
        unset task var
        """

    async def __aexit__(*args):
        """
        unset task var
        """


class ITransactionCache(Interface):
    async def clear():  # type: ignore
        """
        clear cache
        """

    async def get(oid=None, container=None, id=None, variant=None):
        """
        get cached object
        """

    async def set(value, oid=None, container=None, id=None, variant=None):
        """
        set cached data
        """

    async def delete(key):
        """
        delete cache key
        """

    async def delete_all(keys):
        """
        delete list of keys
        """

    async def close():  # type: ignore
        """
        close the cache
        """


class IStorage(Interface):
    """
    interface storage adapters must implement
    """

    async def finalize():  # type: ignore
        """
        Run cleanup
        """

    async def initialize(loop):
        """
        Initialize database
        """

    async def remove():  # type: ignore
        """
        Remove database
        """

    async def load(txn, oid):
        """
        load ob from oid
        """

    async def store(oid, old_serial, writer, obj, txn):
        """
        store oid with obj
        """

    async def delete(txn, oid):
        """
        delete ob by oid
        """

    async def get_next_tid(txn):
        """
        get next transaction id
        """

    async def start_transaction(txn):
        """
        start transaction
        """

    async def get_current_tid(txn):
        """
        Get current tid
        """

    async def get_conflicts(txn):
        """
        get conflicted ob writes
        """

    async def commit(txn):
        """
        Commit current transaction
        """

    async def abort(txn):
        """
        abort transaction
        """

    async def keys(txn, oid):
        """
        get keys for oid
        """

    async def get_child(txn, parent_oid, id):
        """
        get child of parent oid
        """

    async def has_key(txn, parent_oid, id):
        """
        check if key exists
        """

    async def len(txn, oid):
        """
        get length of folder
        """

    async def items(txn, oid):
        """
        get items in a folder
        """

    async def get_annotation(txn, oid, id):
        """
        get annotation
        """

    async def get_annotation_keys(txn, oid):
        """
        get annotation keys
        """

    async def write_blob_chunk(txn, bid, oid, chunk_index, data):
        """
        write blob chunk
        """

    async def read_blob_chunk(txn, bid, chunk=0):
        """
        read blob chunk
        """

    async def read_blob_chunks(txn, bid):
        """
        read blob chunks
        """

    async def del_blob(txn, bid):
        """
        delete blob
        """

    async def close(conn):
        """
        close conn object
        """

    async def terminate(conn):
        """
        terminate conn object
        """


class IPostgresStorage(IStorage):
    objects_table_name = Attribute("")
    sql = Attribute("")
    pool = Attribute("")



class ITransactionStrategy(Interface):
    async def tpc_begin():  # type: ignore
        """
        Begin transaction, should set ._tid on transaction if supports transactions
        """

    async def tpc_vote():  # type: ignore
        """
        Returns true if no conflicts, false if conflicts
        """

    async def tpc_finish():  # type: ignore
        """
        Finish the transaction, committing transaction
        """


class IDBTransactionStrategy(ITransactionStrategy):
    pass


class IDatabaseManager(Interface):
    async def get_names() -> list:  # type: ignore
        """
        Return a list of available databases
        """

    async def create(name: str) -> IStorage:
        """
        Create a new database on the storage
        """

    async def delete(name: str):  # type: ignore
        """
        Delete database on the storage
        """

    async def get_database(name: str) -> IDatabase:
        """
        Return storage instance for database
        """

    async def exists(name: str) -> bool:
        """
        Return whether a db exists or not
        """


class IJSONDBSerializer(ICatalogDataAdapter):
    """
    """


class IVacuumProvider(Interface):
    def __init__(storage):
        """
        Adapts a configured storage
        """

    async def __call__():
        """
        Run vacuuming
        """


class IStorageCreatedEvent(interfaces.IObjectEvent):
    object: IStorage = Attribute("storage that was created")
