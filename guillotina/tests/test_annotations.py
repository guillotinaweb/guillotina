from guillotina.annotations import AnnotationData
from guillotina.content import create_content_in_container
from guillotina.fields.annotation import BucketDictValue
from guillotina.interfaces import IAnnotations
from guillotina.tests.utils import login
from guillotina.transactions import transaction
from guillotina.utils import get_database

import os
import pytest


pytest.mark.skipif(os.environ.get("DATABASE") == "cockroachdb", reason="Flaky cockroachdb test")


async def test_create_annotation(db, guillotina_main):
    db = await get_database("db")
    login()

    async with transaction(db=db):
        container = await create_content_in_container(db, "Container", "container", title="Container")
        ob = await create_content_in_container(container, "Item", "foobar")

        annotations = IAnnotations(ob)
        data = AnnotationData()
        data["foo"] = "bar"
        await annotations.async_set("foobar", data)

    async with transaction(db=db):
        container = await db.async_get("container")
        ob = await container.async_get("foobar")
        annotations = IAnnotations(ob)
        assert "foobar" in (await annotations.async_keys())
        await annotations.async_del("foobar")

    async with transaction(db=db):
        container = await db.async_get("container")
        ob = await container.async_get("foobar")
        annotations = IAnnotations(ob)
        assert "foobar" not in (await annotations.async_keys())
        await container.async_del("foobar")
        await db.async_del("container")


async def test_bucket_dict_value(db, guillotina_main):
    db = await get_database("db")
    login()
    bucket = BucketDictValue(bucket_len=10)

    async with transaction(db=db):
        container = await create_content_in_container(db, "Container", "container", title="Container")
        ob = await create_content_in_container(container, "Item", "foobar")
        for index in range(50):
            await bucket.assign(ob, str(index), index)

        assert len(bucket) == 50
        assert await bucket.get(ob, "1") == 1

    async with transaction(db=db):
        container = await db.async_get("container")
        ob = await container.async_get("foobar")
        await bucket.clear(ob)
        assert len(bucket) == 0
        assert await bucket.get(ob, "1") is None

    async with transaction(db=db):
        container = await db.async_get("container")
        ob = await container.async_get("foobar")
        _range = range(50, 100)
        for index in _range:
            await bucket.assign(ob, str(index), index)

        assert len(bucket) == 50
        assert await bucket.get(ob, "50") == 50

        # Test iter keys, values and items
        assert [k async for k in bucket.keys(ob)] == [str(i) for i in _range]
        assert [v async for v in bucket.values(ob)] == [i for i in _range]
        assert [(k, v) async for k, v in bucket.items(ob)] == [(str(i), i) for i in _range]
