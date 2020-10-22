from datetime import datetime
from guillotina import configure
from guillotina import task_vars
from guillotina.catalog import index
from guillotina.catalog.utils import get_index_fields
from guillotina.catalog.utils import get_metadata_fields
from guillotina.catalog.utils import parse_query
from guillotina.component import get_adapter
from guillotina.component import query_utility
from guillotina.content import Container
from guillotina.content import create_content
from guillotina.content import Resource
from guillotina.directives import index_field
from guillotina.event import notify
from guillotina.events import ObjectModifiedEvent
from guillotina.interfaces import ICatalogDataAdapter
from guillotina.interfaces import ICatalogUtility
from guillotina.interfaces import IResource
from guillotina.interfaces import ISecurityInfo
from guillotina.tests import mocks
from guillotina.tests import utils as test_utils

import json
import os
import pytest


pytestmark = pytest.mark.asyncio


NOT_POSTGRES = os.environ.get("DATABASE", "DUMMY") in ("DUMMY")
PG_CATALOG_SETTINGS = {
    "applications": ["guillotina.contrib.catalog.pg"],
    "load_utilities": {
        "catalog": {
            "provides": "guillotina.interfaces.ICatalogUtility",
            "factory": "guillotina.contrib.catalog.pg.PGSearchUtility",
        }
    },
}


class ICustomItem(IResource):

    pass


@index_field.with_accessor(ICustomItem, "title", type="text", field="title")
def get_title(ob):
    return f"The title is: {ob.title}"


@configure.contenttype(type_name="CustomItem", schema=ICustomItem)
class CustomItem(Resource):
    """
    Basic item content type. Inherits from Resource
    """


async def test_indexed_fields(dummy_guillotina):
    fields = get_index_fields("Item")
    assert "uuid" in fields
    assert "path" in fields
    assert "title" in fields
    assert "creation_date" in fields
    metadata = get_metadata_fields("Example")
    assert len(metadata) == 1


async def test_get_index_data(dummy_txn_root):

    async with dummy_txn_root:
        container = await create_content("Container", id="guillotina", title="Guillotina")
        container.__name__ = "guillotina"

        ob = await create_content("Item", id="foobar")

        data = ICatalogDataAdapter(ob)
        fields = await data()

        assert "type_name" in fields
        assert "uuid" in fields
        assert "path" in fields
        assert "title" in fields


async def test_get_index_data_with_accessors(dummy_txn_root):
    async with dummy_txn_root:
        container = await create_content("Container", id="guillotina", title="Guillotina")
        container.__name__ = "guillotina"

        ob = await create_content("Example", id="foobar", categories=[{"label": "foo", "number": 1}])

        data = ICatalogDataAdapter(ob)
        fields = await data()

        for field_name in (
            "categories_accessor",
            "foobar_accessor",
            "type_name",
            "categories",
            "uuid",
            "path",
            "title",
            "tid",
        ):
            assert field_name in fields

        # now only with indexes specified
        data = ICatalogDataAdapter(ob)
        fields = await data(indexes=["categories"])
        # but should also pull in `foobar_accessor` because it does not
        # have a field specified for it.
        for field_name in (
            "categories_accessor",
            "foobar_accessor",
            "type_name",
            "categories",
            "uuid",
            "tid",
        ):
            assert field_name in fields
        assert "title" not in fields


async def test_override_index_directive(dummy_txn_root):
    container = await create_content("Container", id="guillotina", title="Guillotina")
    container.__name__ = "guillotina"

    ob = await create_content("CustomItem", id="foobar", title="Test")
    data = ICatalogDataAdapter(ob)
    fields = await data()
    assert fields["title"] == "The title is: Test"  # Good, uses the custom accessor

    ob = await create_content("Item", id="foobar", title="Test")
    data = ICatalogDataAdapter(ob)
    fields = await data(indexes=["title"])
    assert fields["title"] == "Test"
    # E       AssertionError: assert 'The title is: Test' == 'Test'
    # E         - The title is: Test
    # E         + Test


async def test_registered_base_utility(dummy_guillotina):
    util = query_utility(ICatalogUtility)
    assert util is not None


async def test_get_security_data(dummy_guillotina):
    ob = test_utils.create_content()
    adapter = get_adapter(ob, ISecurityInfo)
    data = adapter()
    assert "access_users" in data
    assert "access_roles" in data


async def test_get_data_uses_indexes_param(dummy_txn_root):
    async with dummy_txn_root:
        util = query_utility(ICatalogUtility)
        container = await create_content("Container", id="guillotina", title="Guillotina")
        container.__name__ = "guillotina"
        ob = await create_content("Item", id="foobar")
        data = await util.get_data(ob, indexes=["title"])
        assert len(data) == 8  # @uid, type_name, etc always returned
        data = await util.get_data(ob, indexes=["title", "id"])
        assert len(data) == 9

        data = await util.get_data(ob)
        assert len(data) > 10


async def test_modified_event_gathers_all_index_data(dummy_guillotina):
    container = await create_content("Container", id="guillotina", title="Guillotina")
    container.__name__ = "guillotina"
    task_vars.container.set(container)
    ob = await create_content("Item", id="foobar")
    ob.__uuid__ = "foobar"
    await notify(ObjectModifiedEvent(ob, payload={"title": "", "id": ""}))
    fut = index.get_indexer()

    assert len(fut.update["foobar"]) == 9

    await notify(ObjectModifiedEvent(ob, payload={"creation_date": ""}))
    assert "modification_date" in fut.update["foobar"]
    assert len(fut.update["foobar"]) == 10


@pytest.mark.app_settings(PG_CATALOG_SETTINGS)
@pytest.mark.skipif(NOT_POSTGRES, reason="Only PG")
async def test_search_endpoint(container_requester):
    async with container_requester as requester:
        await requester("POST", "/db/guillotina", data=json.dumps({"@type": "Item"}))
        response, status = await requester("GET", "/db/guillotina/@search")
        assert status == 200
        assert len(response["items"]) == 1


@pytest.mark.skipif(not NOT_POSTGRES, reason="Only not PG")
async def test_search_endpoint_no_pg(container_requester):
    async with container_requester as requester:
        response, status = await requester("GET", "/db/guillotina/@search")
        assert status == 200
        assert len(response["items"]) == 0


async def test_search_post_endpoint(container_requester):
    async with container_requester as requester:
        response, status = await requester("POST", "/db/guillotina/@search", data="{}")
        assert status == 200


async def test_reindex_endpoint(container_requester):
    async with container_requester as requester:
        response, status = await requester("POST", "/db/guillotina/@catalog-reindex", data="{}")
        assert status == 200


async def test_async_reindex_endpoint(container_requester):
    async with container_requester as requester:
        response, status = await requester("POST", "/db/guillotina/@async-catalog-reindex", data="{}")
        assert status == 200


async def test_create_catalog(container_requester):
    async with container_requester as requester:
        response, status = await requester("POST", "/db/guillotina/@catalog", data="{}")
        assert status == 200
        response, status = await requester("DELETE", "/db/guillotina/@catalog")
        assert status == 200


@pytest.mark.skipif(NOT_POSTGRES, reason="Only PG")
async def test_query_stored_json(container_requester):
    async with container_requester as requester:
        await requester(
            "POST", "/db/guillotina/", data=json.dumps({"@type": "Item", "title": "Item1", "id": "item1"})
        )
        await requester(
            "POST", "/db/guillotina/", data=json.dumps({"@type": "Item", "title": "Item2", "id": "item2"})
        )

        conn = requester.db.storage.read_conn
        result = await conn.fetch(
            """
select json from {0}
where json->>'type_name' = 'Item' AND json->>'container_id' = 'guillotina'
order by json->>'id'
""".format(
                requester.db.storage._objects_table_name
            )
        )
        print(f"{result}")
        assert len(result) == 2
        assert json.loads(result[0]["json"])["id"] == "item1"
        assert json.loads(result[1]["json"])["id"] == "item2"

        result = await conn.fetch(
            """
select json from {0}
where json->>'id' = 'item1' AND json->>'container_id' = 'guillotina'
""".format(
                requester.db.storage._objects_table_name
            )
        )
        assert len(result) == 1


@pytest.mark.app_settings(PG_CATALOG_SETTINGS)
@pytest.mark.skipif(NOT_POSTGRES, reason="Only PG")
async def test_query_pg_catalog(container_requester):
    from guillotina.contrib.catalog.pg import PGSearchUtility

    async with container_requester as requester:
        await requester(
            "POST", "/db/guillotina/", data=json.dumps({"@type": "Item", "title": "Item1", "id": "item1"})
        )
        await requester(
            "POST", "/db/guillotina/", data=json.dumps({"@type": "Item", "title": "Item2", "id": "item2"})
        )

        async with requester.db.get_transaction_manager() as tm, await tm.begin():
            test_utils.login()
            root = await tm.get_root()
            container = await root.async_get("guillotina")

            util = PGSearchUtility()
            await util.initialize()
            results = await util.search(container, {"id": "item1"})
            assert len(results["items"]) == 1

            results = await util.search(container, {"_size": "1"})
            assert len(results["items"]) == 1
            results = await util.search(container, {"_size": "1", "_from": "1"})
            assert len(results["items"]) == 1

            results = await util.query_aggregation(container, {"_metadata": "title"})
            assert len(results["items"]) == 2
            assert results["items"][0][0] == "Item1"

            results = await util.query_aggregation(container, {"_metadata": ["title", "creators"]})
            assert len(results["items"]) == 2
            assert results["items"][0][1][0] == "root"


@pytest.mark.app_settings(PG_CATALOG_SETTINGS)
@pytest.mark.skipif(NOT_POSTGRES, reason="Only PG")
async def test_fulltext_query_pg_catalog(container_requester):
    from guillotina.contrib.catalog.pg import PGSearchUtility

    async with container_requester as requester:
        await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps({"@type": "Item", "id": "item1", "title": "Something interesting about foobar"}),
        )
        await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps({"@type": "Item", "title": "Something else", "id": "item2"}),
        )

        async with requester.db.get_transaction_manager() as tm, await tm.begin():
            test_utils.login()
            root = await tm.get_root()
            container = await root.async_get("guillotina")

            util = PGSearchUtility()
            await util.initialize()
            results = await util.search(container, {"title": "something"})
            assert len(results["items"]) == 2
            results = await util.search(container, {"title": "interesting"})
            assert len(results["items"]) == 1


@pytest.mark.app_settings(PG_CATALOG_SETTINGS)
@pytest.mark.skipif(NOT_POSTGRES, reason="Only PG")
async def test_build_pg_query(dummy_guillotina):
    from guillotina.contrib.catalog.pg import PGSearchUtility

    util = PGSearchUtility()
    with mocks.MockTransaction():
        content = test_utils.create_content(Container)
        query = parse_query(content, {"uuid": content.uuid}, util)
        assert content.uuid == query["wheres_arguments"][0]
        assert "json->'uuid'" in query["wheres"][0]


async def test_parse_bbb_plone(dummy_guillotina):
    from guillotina.catalog.parser import BaseParser

    content = test_utils.create_content(Container)
    parser = BaseParser(None, content)
    result = parser(
        {"portal_type": "Folder", "SearchableText": "foobar", "b_size": 45, "b_start": 50, "path.depth": 2}
    )
    assert "searchabletext__or" in result["params"]
    assert "title__in" in result["params"]["searchabletext__or"]
    assert "depth" in result["params"]
    assert "type_name" in result["params"]
    assert "portal_type" not in result["params"]
    assert result["_from"] == 50
    assert result["size"] == 45


async def test_parse_base():
    from guillotina.catalog.parser import BaseParser

    content = test_utils.create_content(Container)
    parser = BaseParser(None, content)
    result = parser({"_from": 5, "_sort_asc": "modification_date", "path__starts": "foo/bar"})
    assert result["_from"] == 5
    assert result["sort_on"] == "modification_date"
    assert result["sort_dir"] == "ASC"
    assert result["params"]["path__starts"] == "/foo/bar"

    result = parser({"_sort_des": "modification_date"})
    assert result["sort_on"] == "modification_date"
    assert result["sort_dir"] == "DESC"

    result = parser({"_metadata": "modification_date"})
    result["metadata"] == ["modification_date"]
    result = parser({"_metadata": "_all"})
    result["metadata"] is None

    result = parser({"_metadata_not": "modification_date"})
    result["excluded_metadata"] == ["modification_date"]


async def test_basic_index_generator():
    from guillotina.contrib.catalog.pg import BasicJsonIndex

    index = BasicJsonIndex("foobar")
    assert "json->'" in index.where("foobar", "?")
    assert "json->>'" in index.where("foobar", "=")


async def test_pg_field_parser(dummy_guillotina):
    from guillotina.contrib.catalog.pg import Parser

    content = test_utils.create_content(Container)
    parser = Parser(None, content)

    # test convert operators
    for q1, q2 in (("gte", ">="), ("gt", ">"), ("eq", "="), ("lte", "<="), ("not", "!="), ("lt", "<")):
        where, value, select = parser.process_queried_field(f"depth__{q1}", "2")
        assert f" {q2} " in where
        assert value == [2]

    # bad int
    assert parser.process_queried_field(f"depth__{q1}", "foobar") is None

    # convert bool
    where, value, select = parser.process_queried_field(f"boolean_field", "true")
    assert value == [True]
    where, value, select = parser.process_queried_field(f"boolean_field", "false")
    assert value == [False]

    # none for invalid
    assert parser.process_queried_field(f"foobar", None) is None

    # convert to list
    where, value, select = parser.process_queried_field(f"tags__in", "foo,bar")
    assert value == [["foo", "bar"]]
    assert " ?| " in where

    where, value, select = parser.process_queried_field(f"tags", "bar")
    assert " ? " in where

    where, value, select = parser.process_queried_field(f"tags", ["foo", "bar"])
    assert " ?| " in where

    # date parsing
    where, value, select = parser.process_queried_field(
        f"creation_date__gte", "2019-06-15T18:37:31.008359+00:00"
    )
    assert isinstance(value[0], datetime)

    # path
    where, value, select = parser.process_queried_field(f"path", "/foo/bar")
    assert "substring(json->>" in where

    # ft
    where, value, select = parser.process_queried_field(f"title", "foobar")
    assert "to_tsvector" in where


@pytest.mark.app_settings(PG_CATALOG_SETTINGS)
@pytest.mark.skipif(NOT_POSTGRES, reason="Only PG")
async def test_parse_metadata(dummy_guillotina):
    from guillotina.contrib.catalog.pg import PGSearchUtility

    util = PGSearchUtility()
    with mocks.MockTransaction():
        content = test_utils.create_content(Container)
        query = parse_query(content, {"_metadata": "foobar"})
        result = util.load_meatdata(query, {"foobar": "foobar", "blah": "blah"})
        assert result == {"foobar": "foobar"}

        query = parse_query(content, {"_metadata_not": "foobar"})
        result = util.load_meatdata(query, {"foobar": "foobar", "blah": "blah"})
        assert result == {"blah": "blah"}
