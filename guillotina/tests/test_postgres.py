from guillotina.component import get_adapter
from guillotina.content import Folder
from guillotina.db.interfaces import IVacuumProvider
from guillotina.db.storages.pg import PostgresqlStorage
from guillotina.db.transaction_manager import TransactionManager
from guillotina.exceptions import ConflictError
from guillotina.tests import mocks
from guillotina.tests.utils import create_content
from unittest.mock import Mock
from uuid import uuid4

import asyncio
import asyncpg
import os
import pytest


pytestmark = pytest.mark.asyncio


DATABASE = os.environ.get("DATABASE", "DUMMY")
USE_RDMS = DATABASE != "DUMMY"


async def cleanup(aps):
    conn = await aps.open()
    tm = mocks.MockTransactionManager(aps)
    txn = mocks.MockTransaction(tm)
    txn._db_conn = conn
    await aps.start_transaction(txn)

    conn = txn._db_conn
    await conn.execute("DROP TABLE IF EXISTS objects;")
    await conn.execute("DROP TABLE IF EXISTS blobs;")
    if DATABASE == "postgres":
        await conn.execute("ALTER SEQUENCE tid_sequence RESTART WITH 1")
    await txn._db_txn.commit()
    await aps.pool.release(conn)
    await aps.finalize()


async def get_aps(postgres, strategy=None, pool_size=16, autovacuum=True):
    dsn = "postgres://postgres:@{}:{}/guillotina".format(postgres[0], postgres[1])
    klass = PostgresqlStorage
    if strategy is None:
        strategy = "resolve_readcommitted"
    aps = klass(
        dsn=dsn,
        name="db",
        transaction_strategy=strategy,
        pool_size=pool_size,
        conn_acquire_timeout=0.1,
        autovacuum=autovacuum,
    )
    await aps.initialize()
    return aps


@pytest.mark.skipif(DATABASE == "DUMMY", reason="Not for dummy db")
async def test_read_obs(db, dummy_guillotina):
    """Low level test checks that root is not there"""
    aps = await get_aps(db)
    with TransactionManager(aps) as tm, await tm.begin() as txn:
        ob = create_content()
        txn.register(ob)

        assert len(txn.modified) == 1

        await tm.commit(txn=txn)

        txn = await tm.begin()

        ob2 = await txn.get(ob.__uuid__)

        assert ob2.__uuid__ == ob.__uuid__
        await tm.commit(txn=txn)

        await aps.remove()
        await cleanup(aps)


@pytest.mark.skipif(DATABASE == "DUMMY", reason="Not for dummy db")
async def test_restart_connection(db, dummy_guillotina):
    """Low level test checks that root is not there"""
    aps = await get_aps(db)
    with TransactionManager(aps) as tm, await tm.begin() as txn:
        ob = create_content()
        txn.register(ob)

        assert len(txn.modified) == 1

        await tm.commit(txn=txn)

        with pytest.raises(ConflictError):
            await aps.restart_connection()

        txn = await tm.begin()

        ob2 = await txn.get(ob.__uuid__)

        assert ob2.__uuid__ == ob.__uuid__
        await tm.commit(txn=txn)

        await aps.remove()
        await cleanup(aps)


@pytest.mark.skipif(DATABASE == "DUMMY", reason="Not for dummy db")
async def test_restart_connection_pg(db, dummy_guillotina):
    aps = await get_aps(db)
    with TransactionManager(aps) as tm:
        # Test it works
        await tm._storage.get_next_tid(Mock())

        # Simulate connection was initialized a long time ago
        tm._storage._connection_initialized_on = 0

        async def fetchval_conn_closed():
            raise asyncpg.exceptions.InterfaceError(
                "cannot call PreparedStatement.fetchval(): the underlying connection is closed"
            )

        # Simulate underlying connection is closed
        tm._storage._connection_manager._stmt_next_tid = Mock(**{"fetchval": fetchval_conn_closed})

        with pytest.raises(ConflictError):
            await tm._storage.get_next_tid(Mock())

        # Test works again
        await tm._storage.get_next_tid(Mock())

        await aps.remove()
        await cleanup(aps)


@pytest.mark.skipif(DATABASE in ("DUMMY"), reason="Dummy does not have cascade support")
async def test_deleting_parent_deletes_children(db, dummy_guillotina):
    aps = await get_aps(db)
    with TransactionManager(aps) as tm, await tm.begin() as txn:

        folder = create_content(Folder, "Folder")
        txn.register(folder)
        ob = create_content()
        await folder.async_set("foobar", ob)

        assert len(txn.modified) == 2

        await tm.commit(txn=txn)
        txn = await tm.begin()

        ob2 = await txn.get(ob.__uuid__)
        folder2 = await txn.get(folder.__uuid__)

        assert ob2.__uuid__ == ob.__uuid__
        assert folder2.__uuid__ == folder.__uuid__

        # delete parent, children should be gone...
        txn.delete(folder2)
        assert len(txn.deleted) == 1
        await tm.commit(txn=txn)

        # give delete task a chance to execute
        await asyncio.sleep(0.1)

        txn = await tm.begin()

        with pytest.raises(KeyError):
            await txn.get(ob.__uuid__)
        with pytest.raises(KeyError):
            await txn.get(folder.__uuid__)

        await tm.abort(txn=txn)

        await aps.remove()
        await cleanup(aps)


@pytest.mark.skipif(DATABASE == "DUMMY", reason="Not for dummy db")
async def test_create_blob(db, dummy_guillotina):
    aps = await get_aps(db)
    with TransactionManager(aps) as tm, await tm.begin() as txn:
        ob = create_content()
        txn.register(ob)

        await txn.write_blob_chunk("X" * 32, ob.__uuid__, 0, b"foobar")

        await tm.commit(txn=txn)
        txn = await tm.begin()

        blob_record = await txn.read_blob_chunk("X" * 32, 0)
        assert blob_record["data"] == b"foobar"

        # also get data from ob that started as a stub...
        ob2 = await txn.get(ob.__uuid__)
        assert ob2.type_name == "Item"
        assert "foobar" in ob2.id

        await tm.abort(txn=txn)

        await aps.remove()
        await cleanup(aps)


@pytest.mark.skipif(DATABASE == "DUMMY", reason="Not for dummy db")
async def test_delete_resource_deletes_blob(db, dummy_guillotina):
    aps = await get_aps(db)
    with TransactionManager(aps) as tm, await tm.begin() as txn:
        ob = create_content()
        txn.register(ob)

        await txn.write_blob_chunk("X" * 32, ob.__uuid__, 0, b"foobar")

        await tm.commit(txn=txn)
        txn = await tm.begin()

        ob = await txn.get(ob.__uuid__)
        txn.delete(ob)

        await tm.commit(txn=txn)
        await asyncio.sleep(0.1)  # make sure cleanup runs
        txn = await tm.begin()

        assert await txn.read_blob_chunk("X" * 32, 0) is None

        with pytest.raises(KeyError):
            await txn.get(ob.__uuid__)

        await tm.abort(txn=txn)
        await aps.remove()
        await cleanup(aps)


@pytest.mark.skipif(DATABASE in ("DUMMY"), reason="Dummy not support resolve...")
async def test_should_raise_conflict_error_when_editing_diff_data_with_resolve_strat(db, dummy_guillotina):
    aps = await get_aps(db, "resolve")
    with TransactionManager(aps) as tm, await tm.begin() as txn:
        ob = create_content()
        ob.title = "foobar"
        ob.description = "foobar"
        txn.register(ob)

        await tm.commit(txn=txn)

        # 1 started before 2
        txn1 = await tm.begin()
        txn2 = await tm.begin()

        ob1 = await txn1.get(ob.__uuid__)
        ob2 = await txn2.get(ob.__uuid__)
        ob1.title = "foobar1"
        ob2.description = "foobar2"

        txn1.register(ob1)
        txn2.register(ob2)

        # commit 2 before 1
        await tm.commit(txn=txn2)
        with pytest.raises(ConflictError):
            await tm.commit(txn=txn1)

        await aps.remove()
        await cleanup(aps)


@pytest.mark.skipif(DATABASE in ("DUMMY"), reason="Dummy not support resolve...")
async def test_should_resolve_conflict_error(db, dummy_guillotina):
    aps = await get_aps(db, "resolve")
    with TransactionManager(aps) as tm, await tm.begin() as txn:
        ob1 = create_content()
        ob2 = create_content()
        txn.register(ob1)
        txn.register(ob2)

        await tm.commit(txn=txn)

        # 1 started before 2
        txn1 = await tm.begin()
        txn2 = await tm.begin()

        ob1 = await txn1.get(ob1.__uuid__)
        ob2 = await txn2.get(ob2.__uuid__)

        txn1.register(ob1)
        txn2.register(ob2)

        # commit 2 before 1
        await tm.commit(txn=txn2)
        # should not raise conflict error
        await tm.commit(txn=txn1)

        await aps.remove()
        await cleanup(aps)


@pytest.mark.skipif(DATABASE in ("DUMMY"), reason="Dummy not support resolve...")
async def test_should_not_resolve_conflict_error_with_resolve(db, dummy_guillotina):
    aps = await get_aps(db, "resolve")
    with TransactionManager(aps) as tm, await tm.begin() as txn:

        ob1 = create_content()
        txn.register(ob1)

        await tm.commit(txn=txn)

        # 1 started before 2
        txn1 = await tm.begin()
        txn2 = await tm.begin()

        ob1 = await txn1.get(ob1.__uuid__)
        ob2 = await txn2.get(ob1.__uuid__)

        txn1.register(ob1)
        txn2.register(ob2)

        # commit 2 before 1
        await tm.commit(txn=txn2)
        ob1.__serial__ = txn2._tid  # prevent tid error since we're testing trns conflict error
        with pytest.raises(ConflictError):
            await tm.commit(txn=txn1)

        await aps.remove()
        await cleanup(aps)


@pytest.mark.skipif(DATABASE in ("DUMMY"), reason="Dummy not support resolve...")
async def test_should_not_resolve_conflict_error_with_simple_strat(db, dummy_guillotina):
    aps = await get_aps(db, "simple")
    with TransactionManager(aps) as tm, await tm.begin() as txn:
        ob1 = create_content()
        ob2 = create_content()
        txn.register(ob1)
        txn.register(ob2)

        await tm.commit(txn=txn)

        # 1 started before 2
        txn1 = await tm.begin()
        txn2 = await tm.begin()

        ob1 = await txn1.get(ob1.__uuid__)
        ob2 = await txn2.get(ob2.__uuid__)

        txn1.register(ob1)
        txn2.register(ob2)

        # commit 2 before 1
        await tm.commit(txn=txn2)
        with pytest.raises(ConflictError):
            await tm.commit(txn=txn1)

        await aps.remove()
        await cleanup(aps)


@pytest.mark.skipif(DATABASE == "DUMMY", reason="Not for dummy db")
async def test_none_strat_allows_trans_commits(db, dummy_guillotina):
    aps = await get_aps(db, "none")
    with TransactionManager(aps) as tm, await tm.begin() as txn:

        ob1 = create_content()
        txn.register(ob1)

        await tm.commit(txn=txn)

        txn1 = await tm.begin()
        txn2 = await tm.begin()
        ob1 = await txn1.get(ob1.__uuid__)
        ob2 = await txn2.get(ob1.__uuid__)
        ob1.title = "foobar1"
        ob2.title = "foobar2"
        txn1.register(ob1)
        txn2.register(ob2)

        await tm.commit(txn=txn2)
        await tm.commit(txn=txn1)

        txn = await tm.begin()
        ob1 = await txn.get(ob1.__uuid__)
        assert ob1.title == "foobar1"

        await tm.abort(txn=txn)

        await aps.remove()
        await cleanup(aps)


@pytest.mark.skipif(DATABASE == "DUMMY", reason="Not for dummy db")
async def test_count_total_objects(db, dummy_guillotina):
    aps = await get_aps(db)
    with TransactionManager(aps) as tm, await tm.begin() as txn:

        ob = create_content()
        txn.register(ob)

        await tm.commit(txn=txn)
        txn = await tm.begin()

        assert await txn.get_total_number_of_objects() == 2
        assert await txn.get_total_number_of_resources() == 1

        await tm.abort(txn=txn)

        await aps.remove()
        await cleanup(aps)


@pytest.mark.skipif(DATABASE == "DUMMY", reason="Not for dummy db")
async def test_get_resources_of_type(db, dummy_guillotina):
    aps = await get_aps(db)
    with TransactionManager(aps) as tm, await tm.begin() as txn:

        ob = create_content()
        txn.register(ob)

        await tm.commit(txn=txn)
        txn = await tm.begin()

        count = 0
        async for item in txn._get_resources_of_type("Item"):
            assert item["type"] == "Item"
            count += 1

        assert count == 1

        await tm.abort(txn=txn)

        await aps.remove()
        await cleanup(aps)


@pytest.mark.skipif(DATABASE == "DUMMY", reason="Not for dummy db")
async def test_get_total_resources_of_type(db, dummy_guillotina):
    aps = await get_aps(db)
    with TransactionManager(aps) as tm, await tm.begin() as txn:
        ob = create_content()
        txn.register(ob)

        await tm.commit(txn=txn)
        txn = await tm.begin()

        assert 1 == await txn.get_total_resources_of_type("Item")

        await tm.abort(txn=txn)

        await aps.remove()
        await cleanup(aps)


@pytest.mark.skipif(DATABASE == "DUMMY", reason="Not for dummy db")
async def test_using_gather_with_queries_before_prepare(db, dummy_guillotina):
    aps = await get_aps(db)
    with TransactionManager(aps) as tm, await tm.begin() as txn:
        ob1 = create_content()
        txn.register(ob1)

        await tm.commit(txn=txn)

        txn = await tm.begin()

        async def get_ob():
            await txn.get(ob1.__uuid__)

        # before we introduced locking on the connection, this would error
        await asyncio.gather(get_ob(), get_ob(), get_ob(), get_ob(), get_ob())

        await tm.abort(txn=txn)

        await aps.remove()
        await cleanup(aps)


@pytest.mark.skipif(DATABASE == "DUMMY", reason="Not for dummy db")
async def test_using_gather_with_queries_after_prepare(db, dummy_guillotina):
    aps = await get_aps(db)
    with TransactionManager(aps) as tm, await tm.begin() as txn:
        ob1 = create_content()
        txn.register(ob1)

        await tm.commit(txn=txn)

        txn = await tm.begin()

        async def get_ob():
            await txn.get(ob1.__uuid__)

        # one initial call should load prepared statement
        await txn.get(ob1.__uuid__)

        # before we introduction locking on the connection, this would error
        await asyncio.gather(get_ob(), get_ob(), get_ob(), get_ob(), get_ob())

        await tm.abort(txn=txn)

        await aps.remove()
        await cleanup(aps)


@pytest.mark.skipif(DATABASE == "DUMMY", reason="Not for dummy db")
async def test_exhausting_pool_size(db, dummy_guillotina):
    # base aps uses 1 connection from the pool for starting transactions
    aps = await get_aps(db, pool_size=2)
    with TransactionManager(aps) as tm, await tm.begin() as txn:
        await txn.get_connection()

        with pytest.raises(asyncio.TimeoutError):
            # should throw an error because we've run out of connections in pool
            txn2 = await tm.begin()
            await txn2.get_connection()

        await tm.abort(txn=txn)

        await aps.remove()
        await cleanup(aps)


@pytest.mark.skipif(DATABASE == "DUMMY", reason="Not for dummy db")
async def test_mismatched_tid_causes_conflict_error(db, dummy_guillotina):

    # base aps uses 1 connection from the pool for starting transactions
    aps = await get_aps(db)
    with TransactionManager(aps) as tm, await tm.begin() as txn:
        ob1 = create_content()
        txn.register(ob1)
        await tm.commit(txn=txn)

        txn = await tm.begin()
        ob1 = await txn.get(ob1.__uuid__)
        # modify p_serial, try committing, should raise conflict error
        ob1.__serial__ = 3242432
        txn.register(ob1)

        with pytest.raises(ConflictError):
            await tm.commit(txn=txn)
        await aps.remove()
        await cleanup(aps)


@pytest.mark.skipif(DATABASE == "DUMMY", reason="Not for dummy db")
async def test_iterate_keys(db, dummy_guillotina):

    # base aps uses 1 connection from the pool for starting transactions
    aps = await get_aps(db)
    with TransactionManager(aps) as tm, await tm.begin() as txn:

        parent = create_content()
        txn.register(parent)
        original_keys = []
        for _ in range(50):
            item = create_content()
            original_keys.append(item.id)
            item.__parent__ = parent
            txn.register(item)

        await tm.commit(txn=txn)
        txn = await tm.begin()

        keys = []
        async for key in txn.iterate_keys(parent.__uuid__, 2):
            keys.append(key)

        assert len(keys) == 50
        assert len(set(keys) - set(original_keys)) == 0
        await tm.abort(txn=txn)


@pytest.mark.skipif(DATABASE in ("DUMMY"), reason="Dummy not support resolve...")
async def test_handles_asyncpg_trying_savepoints(db, dummy_guillotina):

    aps = await get_aps(db)
    tm = TransactionManager(aps)
    # simulate transaction already started(should not happen)
    for conn in tm._storage.pool._queue._queue:
        if conn._con is None:
            await conn.connect()
        conn._con._top_xact = asyncpg.transaction.Transaction(conn._con, "read_committed", False, False)

    with await tm.begin() as txn, tm:

        # then, try doing stuff...
        ob = create_content()
        txn.register(ob)

        assert len(txn.modified) == 1

        await tm.commit(txn=txn)

        txn = await tm.begin()

        ob2 = await txn.get(ob.__uuid__)

        assert ob2.__uuid__ == ob.__uuid__
        await tm.commit(txn=txn)

        await aps.remove()
        await cleanup(aps)


@pytest.mark.skipif(DATABASE in ("DUMMY"), reason="Dummy not support resolve...")
async def test_handles_asyncpg_trying_txn_with_manual_txn(db, dummy_guillotina):

    aps = await get_aps(db)
    tm = TransactionManager(aps)
    # simulate transaction already started(should not happen)
    for conn in tm._storage.pool._queue._queue:
        if conn._con is None:
            await conn.connect()
        await conn._con.execute("BEGIN;")

    with await tm.begin() as txn, tm:
        # then, try doing stuff...
        ob = create_content()
        txn.register(ob)

        assert len(txn.modified) == 1

        await tm.commit(txn=txn)

        txn = await tm.begin()

        ob2 = await txn.get(ob.__uuid__)

        assert ob2.__uuid__ == ob.__uuid__
        await tm.commit(txn=txn)

        await aps.remove()
        await cleanup(aps)


@pytest.mark.skipif(DATABASE in ("DUMMY",), reason="only for rdms")
async def test_vacuum_objects(db, dummy_guillotina):
    aps = await get_aps(db, autovacuum=False)
    tm = TransactionManager(aps)

    # create objects first, commit it...
    txn = await tm.begin()

    ob1 = create_content()
    ob2 = create_content()
    txn.register(ob1)
    txn.register(ob2)

    with txn, tm:
        await tm.commit(txn=txn)

        txn = await tm.begin()
        txn.delete(ob1)
        assert len(txn.deleted) == 1
        await tm.commit(txn=txn)

    async with aps.pool.acquire() as conn:
        result = await conn.fetch("select * from objects where zoid=$1;", ob1.__uuid__)
        assert len(result) == 1
        # deferenced
        assert result[0]["parent_id"] == "D" * 32

    vacuumer = get_adapter(aps, IVacuumProvider)
    await vacuumer()

    await asyncio.sleep(0.1)

    async with aps.pool.acquire() as conn:
        result = await conn.fetch("select * from objects where zoid=$1;", ob1.__uuid__)
        assert len(result) == 0

    await aps.remove()
    await cleanup(aps)


@pytest.mark.skipif(DATABASE in ("DUMMY",), reason="only for rdms")
async def test_constraint_error_inserting_duplicate_annotations(db, dummy_guillotina):
    aps = await get_aps(db, autovacuum=False)
    tm = TransactionManager(aps)

    # create objects first, commit it...
    txn = await tm.begin()

    ob1 = create_content()
    txn.register(ob1)

    with txn, tm:
        await tm.commit(txn=txn)

    async with aps.pool.acquire() as conn:
        # first ok
        await conn.execute(
            f"""
insert into objects (tid, state_size, part, zoid, resource, of, id, type)
values(0, 0, 0, $1, $2, $3, $4, $5)""",
            str(uuid4()),
            True,
            ob1.__uuid__,
            "foo",
            "Item",
        )
    async with aps.pool.acquire() as conn:
        # should fail
        with pytest.raises(asyncpg.exceptions.UniqueViolationError):
            await conn.execute(
                f"""
    insert into objects (tid, state_size, part, zoid, resource, of, id, type)
    values(0, 0, 0, $1, $2, $3, $4, $5)""",
                str(uuid4()),
                True,
                ob1.__uuid__,
                "foo",
                "Item",
            )

    await aps.remove()
    await cleanup(aps)
