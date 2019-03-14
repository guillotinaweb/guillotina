import pytest
from guillotina.contentapi import ContentAPI
from guillotina.utils import get_content_path


async def test_contentapi_create(db, guillotina_main):
    async with ContentAPI(guillotina_main.root['db']) as api:
        container = await api.create({'@type': 'Container', 'id': 'foobar'})
        await api.use_container(container)
        await api.create({'@type': 'Item', 'id': 'foobar'}, in_=container)
        item = await api.get('foobar', in_=container)
        assert get_content_path(item) == '/foobar'
        await api.delete(container)


@pytest.mark.flaky(reruns=3)
async def test_contentapi_delete(db, guillotina_main):
    async with ContentAPI(guillotina_main.root['db']) as api:
        container = await api.create({'@type': 'Container', 'id': 'foobar'})
        await api.use_container(container)
        item = await api.create({'@type': 'Item', 'id': 'foobar'}, in_=container)
        assert get_content_path(item) == '/foobar'
        await api.delete(item)
        assert await api.get('foobar', in_=container) is None
        await api.delete(container)
