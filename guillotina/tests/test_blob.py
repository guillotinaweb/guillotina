from guillotina.blob import Blob
from guillotina.component import getUtility
from guillotina.content import create_content_in_container
from guillotina.interfaces import IApplication
from guillotina.tests.utils import get_mocked_request
from guillotina.tests.utils import login


async def test_create_blob(postgres, guillotina_main):
    root = getUtility(IApplication, name='root')
    db = root['db']
    request = get_mocked_request(db)
    login(request)

    txn = await request._tm.begin(request=request)

    container = await create_content_in_container(
        db, 'Container', 'container', request=request,
        title='Container')

    blob = Blob(container)
    container.blob = blob

    await request._tm.commit(txn=txn)
    txn = await request._tm.begin(request=request)

    container = await db.async_get('container')
    assert blob.bid == container.blob.bid
    assert blob.resource_zoid == container._p_oid
    await db.async_del('container')

    await request._tm.commit(txn=txn)


async def test_write_blob_data(postgres, guillotina_main):
    root = getUtility(IApplication, name='root')
    db = root['db']
    request = get_mocked_request(db)
    login(request)

    txn = await request._tm.begin(request=request)

    container = await create_content_in_container(
        db, 'Container', 'container', request=request,
        title='Container')

    blob = Blob(container)
    container.blob = blob

    blobfi = blob.open('w')
    await blobfi.async_write(b'foobar')

    await request._tm.commit(txn=txn)
    txn = await request._tm.begin(request=request)

    container = await db.async_get('container')
    assert await container.blob.open().async_read() == b'foobar'
    assert container.blob.size == 6
    assert container.blob.chunks == 1

    await db.async_del('container')

    await request._tm.commit(txn=txn)


async def test_write_large_blob_data(postgres, guillotina_main):
    root = getUtility(IApplication, name='root')
    db = root['db']
    request = get_mocked_request(db)
    login(request)

    txn = await request._tm.begin(request=request)

    container = await create_content_in_container(
        db, 'Container', 'container', request=request,
        title='Container')

    blob = Blob(container)
    container.blob = blob

    multiplier = 999999

    blobfi = blob.open('w')
    await blobfi.async_write(b'foobar' * multiplier)

    await request._tm.commit(txn=txn)
    txn = await request._tm.begin(request=request)

    container = await db.async_get('container')
    assert await container.blob.open().async_read() == (b'foobar' * multiplier)
    assert container.blob.size == len(b'foobar' * multiplier)
    assert container.blob.chunks == 6

    await db.async_del('container')

    await request._tm.commit(txn=txn)
