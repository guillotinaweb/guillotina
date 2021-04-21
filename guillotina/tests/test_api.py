from datetime import datetime
from guillotina import configure
from guillotina import schema
from guillotina.addons import Addon
from guillotina.behaviors.attachment import IAttachment
from guillotina.behaviors.dublincore import IDublinCore
from guillotina.interfaces import IAnnotations
from guillotina.interfaces import IFile
from guillotina.interfaces import IResource
from guillotina.test_package import ITestBehavior
from guillotina.tests import utils
from guillotina.tests.dbusers.settings import DEFAULT_SETTINGS as DBUSERS_DEFAULT_SETTINGS
from guillotina.transactions import transaction
from guillotina.utils import get_behavior
from zope.interface import Interface

import base64
import json
import pytest


class ITestingRegistry(Interface):  # pylint: disable=E0239
    enabled = schema.Bool(title="Example attribute")
    test_type = schema.Int(title="Example attribute")


class ITestingRegistryUpdated(Interface):  # pylint: disable=E0239
    enabled = schema.Bool(title="Example attribute")
    test = schema.Bool(title="Example attribute")


@configure.addon(name="testaddon", title="Test addon")
class TestAddon(Addon):
    @classmethod
    def install(cls, container, request):
        Addon.install(container, request)

    @classmethod
    def uninstall(cls, container, request):
        Addon.uninstall(container, request)


@configure.addon(name="testaddon-dependson", dependencies=["testaddon"], title="Test addon with dependency")
class TestAddonDependency(Addon):
    @classmethod
    def install(cls, container, request):
        Addon.install(container, request)

    @classmethod
    def uninstall(cls, container, request):
        Addon.uninstall(container, request)


async def test_get_root(container_requester):
    async with container_requester as requester:
        response, _ = await requester("GET", "/")
        assert response["static_directory"] == ["static", "module_static", "jsapp_static"]
        assert "db" in response["databases"]
        assert "db-custom" in response["databases"]
        assert response["static_file"] == ["favicon.ico"]


async def test_get_database(container_requester):
    """Get the database object."""
    async with container_requester as requester:
        response, _ = await requester("GET", "/db")
        assert len(response["containers"]) == 1


async def test_get_guillotina(container_requester):
    """Get the root guillotina container."""
    async with container_requester as requester:
        response, _ = await requester("GET", "/db/guillotina")
        assert len(response["items"]) == 0


async def test_get_contenttypes(container_requester):
    """Check list of content types."""
    async with container_requester as requester:
        response, status = await requester("GET", "/db/guillotina/@types")
        assert status == 200
        assert len(response) > 1
        assert any("Item" in s["title"] for s in response)
        assert any("Container" in s["title"] for s in response)


async def test_get_contenttype(container_requester):
    """Get a content type definition."""
    async with container_requester as requester:
        response, status = await requester("GET", "/db/guillotina/@types/Item")
        assert status == 200
        assert len(response["components"]["schemas"]) == 1
        assert response["title"] == "Item"


async def test_get_registries(container_requester):
    """Get the list of registries."""
    async with container_requester as requester:
        response, status = await requester("GET", "/db/guillotina/@registry")
        assert status == 200
        assert len(response["value"]) == 2
        assert "guillotina.interfaces.registry.ILayers.active_layers" in response["value"]


async def test_get_registry_value(container_requester):
    """Check a value from registry."""
    async with container_requester as requester:
        response, _ = await requester(
            "GET", "/db/guillotina/@registry/guillotina.interfaces.registry.ILayers.active_layers"
        )
        assert response["value"] == []


async def test_create_container_with_addons(container_requester):
    async with container_requester as requester:
        _, status = await requester(
            "POST",
            "/db",
            data=json.dumps(
                {"@type": "Container", "@addons": ["testaddon"], "title": "foobar", "id": "foobar"}
            ),
        )

        response, status = await requester("GET", "/db/foobar/@addons")
        assert status == 200
        assert "testaddon" in response["installed"]


async def test_create_container_schemavalidation(container_requester):
    async with container_requester as requester:
        _, status = await requester(
            "POST", "/db", data=json.dumps({"@type": "Container", "title": "foobar", "i": "foobar"})
        )
        assert status == 412


async def test_create_container_with_bad_addons(container_requester):
    async with container_requester as requester:
        _, status = await requester(
            "POST",
            "/db",
            data=json.dumps(
                {"@type": "Container", "@addons": ["testaddoninvalid"], "title": "foobar", "id": "foobar"}
            ),
        )
        assert status == 412


async def test_create_content(container_requester):
    async with container_requester as requester:
        _, status = await requester(
            "POST", "/db/guillotina/", data=json.dumps({"@type": "Item", "title": "Item1", "id": "item1"})
        )

        assert status == 201
        _, status = await requester("GET", "/db/guillotina/item1")
        assert _["@static_behaviors"][0] == "guillotina.behaviors.dublincore.IDublinCore"
        root = await utils.get_root(db=requester.db)
        async with transaction(db=requester.db, abort_when_done=True):
            container = await root.async_get("guillotina")
            obj = await container.async_get("item1")
            assert obj.title == "Item1"


async def test_put_content(container_requester):
    async with container_requester as requester:
        data = "WFhY" * 1024 + "WA=="
        _, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps(
                {
                    "@type": "Item",
                    "title": "Item1",
                    "id": "item1",
                    "@behaviors": [IAttachment.__identifier__],
                    IDublinCore.__identifier__: {
                        "title": "foo",
                        "description": "bar",
                        "tags": ["one", "two"],
                    },
                    IAttachment.__identifier__: {
                        "file": {
                            "filename": "foobar.jpg",
                            "content-type": "image/jpeg",
                            "encoding": "base64",
                            "data": data,
                        }
                    },
                }
            ),
        )
        assert status == 201
        _, status = await requester(
            "PUT",
            "/db/guillotina/item1",
            data=json.dumps(
                {"@behaviors": [IAttachment.__identifier__], IDublinCore.__identifier__: {"title": "foobar"}}
            ),
        )
        resp, status = await requester("GET", "/db/guillotina/item1")
        assert resp[IDublinCore.__identifier__]["tags"] is None
        assert resp[IAttachment.__identifier__]["file"] is None

        root = await utils.get_root(db=requester.db)
        async with transaction(db=requester.db, abort_when_done=True):
            container = await root.async_get("guillotina")
            obj = await container.async_get("item1")
            assert obj.title == "foobar"
            with pytest.raises(AttributeError):
                obj.description


async def test_create_content_types_does_not_exist(container_requester):
    async with container_requester as requester:
        resp, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps({"@type": "ItemTypeThatDoesNotExist", "title": "Item1", "id": "item1"}),
        )
        assert status == 412
        assert resp["message"] == "Invalid type: ItemTypeThatDoesNotExist"


async def test_create_delete_contenttype(container_requester):
    """Create and delete a content type."""
    async with container_requester as requester:
        _, status = await requester(
            "POST", "/db/guillotina/", data=json.dumps({"@type": "Item", "title": "Item1", "id": "item1"})
        )
        assert status == 201
        _, status = await requester("DELETE", "/db/guillotina/item1")
        assert status == 200


async def test_404(container_requester):
    """Create and delete a content type."""
    async with container_requester as requester:
        _, status = await requester("GET", "/db/guillotina/sdflksdljfkdsk")
        assert status == 404
        _, status = await requester("GET", "/db/sdflksdljfkdsk")
        assert status == 404
        _, status = await requester("GET", "/sdflksdljfkdsk")
        assert status == 404


async def test_register_registry(container_requester):
    async with container_requester as requester:
        # JSON schema validation
        _, status = await requester(
            "POST", "/db/guillotina/@registry", data=json.dumps({"initial_values": {"enabled": True}})
        )
        assert status == 412

        response, status = await requester(
            "POST",
            "/db/guillotina/@registry",
            data=json.dumps(
                {
                    "interface": "guillotina.tests.test_api.ITestingRegistry",
                    "initial_values": {"enabled": True},
                }
            ),
        )
        assert status == 201

        # JSON Schema validation
        _, status = await requester(
            "PATCH",
            "/db/guillotina/@registry/guillotina.tests.test_api.ITestingRegistry.enabled",
            data=json.dumps({"v": False}),
        )
        assert status == 412

        # Type validation
        response, status = await requester(
            "PATCH",
            "/db/guillotina/@registry/guillotina.tests.test_api.ITestingRegistry.test_type",
            data=json.dumps({"value": ["Im not an integer"]}),
        )
        print(response)
        assert status == 412

        response, status = await requester(
            "PATCH",
            "/db/guillotina/@registry/guillotina.tests.test_api.ITestingRegistry.enabled",
            data=json.dumps({"value": False}),
        )
        assert status == 204
        response, status = await requester(
            "GET", "/db/guillotina/@registry/guillotina.tests.test_api.ITestingRegistry.enabled"
        )
        assert {"value": False} == response

        # this emulates a registry update
        from guillotina.tests import test_api

        test_api.ITestingRegistry = ITestingRegistryUpdated

        response, status = await requester(
            "PATCH",
            "/db/guillotina/@registry/guillotina.tests.test_api.ITestingRegistry.test",
            data=json.dumps({"value": True}),
        )
        assert status == 204
        response, status = await requester(
            "GET", "/db/guillotina/@registry/guillotina.tests.test_api.ITestingRegistry.test"
        )
        assert {"value": True} == response


async def test_create_contenttype_with_date(container_requester):
    async with container_requester as requester:
        _, status = await requester(
            "POST", "/db/guillotina/", data=json.dumps({"@type": "Item", "title": "Item1", "id": "item1"})
        )
        assert status == 201
        date_to_test = "2016-11-30T14:39:07.394273+01:00"
        _, status = await requester(
            "PATCH",
            "/db/guillotina/item1",
            data=json.dumps(
                {
                    "guillotina.behaviors.dublincore.IDublinCore": {
                        "creation_date": date_to_test,
                        "expiration_date": date_to_test,
                    }
                }
            ),
        )

        root = await utils.get_root(db=requester.db)
        async with transaction(db=requester.db, abort_when_done=True):
            container = await root.async_get("guillotina")
            obj = await container.async_get("item1")
            from guillotina.behaviors.dublincore import IDublinCore

            behavior = IDublinCore(obj)
            await behavior.load()
            assert behavior.creation_date.isoformat() == date_to_test  # pylint: disable=E1101
            assert behavior.expiration_date.isoformat() == date_to_test  # pylint: disable=E1101


async def test_create_duplicate_id(container_requester):
    async with container_requester as requester:
        _, status = await requester(
            "POST", "/db/guillotina/", data=json.dumps({"@type": "Item", "title": "Item1", "id": "item1"})
        )
        assert status == 201
        _, status = await requester(
            "POST", "/db/guillotina/", data=json.dumps({"@type": "Item", "title": "Item1", "id": "item1"})
        )
        assert status == 409


async def test_create_nested_object(container_requester):
    async with container_requester as requester:
        _, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps(
                {
                    "@type": "Example",
                    "title": "Item1",
                    "id": "item1",
                    "categories": [{"label": "term1", "number": 1.0}, {"label": "term2", "number": 2.0}],
                }
            ),
        )
        assert status == 201


async def test_get_addons(container_requester):
    async with container_requester as requester:
        _, status = await requester("GET", "/db/guillotina/@addons")
        assert status == 200


async def test_install_invalid_addon_should_give_error(container_requester):
    async with container_requester as requester:
        _, status = await requester("POST", "/db/guillotina/@addons", data=json.dumps({"id": "foobar"}))
        assert status == 412


async def test_install_addons(container_requester):
    id_ = "testaddon"
    async with container_requester as requester:
        response, status = await requester("POST", "/db/guillotina/@addons", data=json.dumps({"id": id_}))
        assert status == 200
        assert id_ in response["installed"]


async def test_install_addons_schema_validate(container_requester):
    id_ = "testaddon"
    async with container_requester as requester:
        _, status = await requester("POST", "/db/guillotina/@addons", data=json.dumps({"i": id_}))
        assert status == 412


async def test_install_addon_with_dep(container_requester):
    id_ = "testaddon-dependson"
    async with container_requester as requester:
        response, status = await requester("POST", "/db/guillotina/@addons", data=json.dumps({"id": id_}))
        assert status == 200
        assert id_ in response["installed"]
        assert "testaddon" in response["installed"]


async def test_install_same_addon_twice_gives_error(container_requester):
    id_ = "testaddon"
    async with container_requester as requester:
        response, status = await requester("POST", "/db/guillotina/@addons", data=json.dumps({"id": id_}))
        assert status == 200
        assert id_ in response["installed"]
        response, status = await requester("POST", "/db/guillotina/@addons", data=json.dumps({"id": id_}))
        assert status == 412


async def test_uninstall_addons(container_requester):
    id_ = "testaddon"
    async with container_requester as requester:
        await requester("POST", "/db/guillotina/@addons", data=json.dumps({"id": id_}))

        response, status = await requester("DELETE", "/db/guillotina/@addons", data=json.dumps({"id": id_}))
        assert status == 200
        assert response is None


async def test_uninstall_addons_schema_validation(container_requester):
    id_ = "testaddon"
    async with container_requester as requester:
        await requester("POST", "/db/guillotina/@addons", data=json.dumps({"id": id_}))

        _, status = await requester("DELETE", "/db/guillotina/@addons", data=json.dumps({"i": id_}))
        assert status == 412


async def test_uninstall_addons_path(container_requester):
    id_ = "testaddon"
    async with container_requester as requester:
        await requester("POST", "/db/guillotina/@addons", data=json.dumps({"id": id_}))

        response, status = await requester("DELETE", f"/db/guillotina/@addons/{id_}")
        assert status == 200
        assert response is None


async def test_uninstall_invalid_addon(container_requester):
    async with container_requester as requester:
        _, status = await requester("DELETE", "/db/guillotina/@addons", data=json.dumps({"id": "foobar"}))
        assert status == 412

        _, status = await requester(
            "DELETE", "/db/guillotina/@addons", data=json.dumps({"id": "testaddon"})  # not installed yet...
        )
        assert status == 412


async def test_get_logged_user_info(container_requester):
    async with container_requester as requester:
        response, status = await requester("GET", "/db/guillotina/@user")
        assert status == 200
        from guillotina.auth.users import ROOT_USER_ID

        try:
            info = response[ROOT_USER_ID]
            assert "Managers" in info["groups"]
        except KeyError:
            raise AssertionError(
                "Code should not come here! as User `%s` " "should be in response" % ROOT_USER_ID
            )


async def test_not_create_content_with_invalid_id(container_requester):
    async with container_requester as requester:
        _, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps({"@type": "Item", "title": "Item1", "id": "lsdkfjl?#($)"}),
        )
        assert status == 412


async def test_get_api_def(container_requester):
    async with container_requester as requester:
        _, status = await requester("GET", "/@apidefinition")
        assert status == 200


async def test_get_subscribers(container_requester):
    async with container_requester as requester:
        response, status = await requester("GET", "/@component-subscribers")
        resource = response["guillotina.interfaces.content.IResource"]
        modified = resource["guillotina.interfaces.events.IObjectPermissionsModifiedEvent"]
        assert modified == ["guillotina.catalog.index.security_changed"]
        assert status == 200


async def test_move_content(container_requester):
    async with container_requester as requester:
        _, status = await requester(
            "POST", "/db/guillotina/", data=json.dumps({"@type": "Folder", "id": "container1"})
        )
        _, status = await requester(
            "POST", "/db/guillotina/", data=json.dumps({"@type": "Folder", "id": "container2"})
        )
        response, status = await requester(
            "POST", "/db/guillotina/", data=json.dumps({"@type": "Folder", "id": "container3"})
        )
        container3_uid = response["@uid"]
        _, status = await requester(
            "POST", "/db/guillotina/container1", data=json.dumps({"@type": "Item", "id": "foobar"})
        )

        _, status = await requester(
            "POST", "/db/guillotina/container1/foobar/@move", data=json.dumps({"destination": "/wrong_path"})
        )
        assert status == 412
        _, status = await requester(
            "POST", "/db/guillotina/container1/foobar/@move", data=json.dumps({"destination": "wrong_uid"})
        )
        assert status == 412

        _, status = await requester(
            "POST", "/db/guillotina/container1/foobar/@move", data=json.dumps({"destination": "/container2"})
        )

        _, status = await requester("GET", "/db/guillotina/container2/foobar")
        assert status == 200
        _, status = await requester("GET", "/db/guillotina/container1/foobar")
        assert status == 404

        _, status = await requester(
            "POST", "/db/guillotina/container2/foobar/@move", data=json.dumps({"destination": container3_uid})
        )

        _, status = await requester("GET", "/db/guillotina/container3/foobar")
        assert status == 200
        _, status = await requester("GET", "/db/guillotina/container2/foobar")
        assert status == 404

        # move back with new id
        _, status = await requester(
            "POST",
            "/db/guillotina/container3/foobar/@move",
            data=json.dumps({"destination": "/container1", "new_id": "foobar_new"}),
        )

        _, status = await requester("GET", "/db/guillotina/container1/foobar_new")
        assert status == 200
        _, status = await requester("GET", "/db/guillotina/container3/foobar")
        assert status == 404


async def test_not_allowed_move_to_same_parent(container_requester):
    async with container_requester as requester:
        _, status = await requester(
            "POST", "/db/guillotina/", data=json.dumps({"@type": "Folder", "id": "folder"})
        )
        _, status = await requester(
            "POST", "/db/guillotina/folder/@move", data=json.dumps({"destination": "/"})
        )
        assert status == 409

        _, status = await requester(
            "POST", "/db/guillotina/folder/@move", data=json.dumps({"new_id": "folder-2"})
        )
        assert status == 200


async def test_not_allowed_move_to_self(container_requester):
    async with container_requester as requester:
        _, status = await requester("POST", "/db/guillotina/@move", data=json.dumps({"destination": "/"}))
        assert status == 412


async def test_duplicate_content(container_requester):
    async with container_requester as requester:
        await requester("POST", "/db/guillotina/", data=json.dumps({"@type": "Item", "id": "foobar1"}))
        await requester("POST", "/db/guillotina/foobar1/@duplicate")
        response, _ = await requester("GET", "/db/guillotina/@ids")
        assert len(response) == 2

        await requester("POST", "/db/guillotina/foobar1/@duplicate", data=json.dumps({"new_id": "foobar2"}))

        response, _ = await requester("GET", "/db/guillotina/@ids")
        assert len(response) == 3
        assert "foobar2" in response
        assert "foobar1" in response

        _, status = await requester(
            "POST", "/db/guillotina/foobar1/@duplicate", data=json.dumps({"destination": "/wrong_path"})
        )
        assert status == 412
        _, status = await requester(
            "POST", "/db/guillotina/foobar1/@duplicate", data=json.dumps({"destination": "wrong_uid"})
        )
        assert status == 412

        response, _ = await requester(
            "POST", "/db/guillotina/", data=json.dumps({"@type": "Folder", "id": "folder"})
        )
        folder_uid = response["@uid"]

        await requester(
            "POST",
            "/db/guillotina/foobar1/@duplicate",
            data=json.dumps({"new_id": "foobar1", "destination": "/folder"}),
        )

        response, _ = await requester("GET", "/db/guillotina/folder/@ids")
        assert len(response) == 1
        assert "foobar1" in response

        await requester(
            "POST",
            "/db/guillotina/foobar1/@duplicate",
            data=json.dumps({"new_id": "foobar2", "destination": folder_uid}),
        )

        response, _ = await requester("GET", "/db/guillotina/folder/@ids")
        assert len(response) == 2
        assert "foobar1" in response
        assert "foobar2" in response


@pytest.mark.app_settings(DBUSERS_DEFAULT_SETTINGS)
async def test_duplicate_and_move_always_checks_permission_on_destination(dbusers_requester):
    async with dbusers_requester as requester:
        # Add Bob user
        _, status = await requester(
            "POST",
            "/db/guillotina/users",
            data=json.dumps(
                {
                    "@type": "User",
                    "name": "Bob",
                    "id": "bob",
                    "username": "bob",
                    "email": "bob@foo.com",
                    "password": "bob",
                }
            ),
        )
        assert status in (200, 201)

        # Add Alice user
        _, status = await requester(
            "POST",
            "/db/guillotina/users",
            data=json.dumps(
                {
                    "@type": "User",
                    "name": "Alice",
                    "id": "alice",
                    "username": "alice",
                    "email": "alice@foo.com",
                    "password": "alice",
                }
            ),
        )
        assert status in (200, 201)

        bob_token = base64.b64encode(b"bob:bob").decode("ascii")
        alice_token = base64.b64encode(b"alice:alice").decode("ascii")

        # Bob creates a file in its folder
        _, status = await requester(
            "POST",
            "/db/guillotina/users/bob/",
            data=json.dumps({"@type": "Item", "id": "foobar1"}),
            auth_type="Basic",
            token=bob_token,
        )
        assert status in (200, 201)

        # Shares it with alice as manager
        _, status = await requester(
            "POST",
            "/db/guillotina/users/bob/foobar1/@sharing",
            data=json.dumps(
                {"prinrole": [{"principal": "alice", "role": "guillotina.Owner", "setting": "Allow"}]}
            ),
            auth_type="Basic",
            token=bob_token,
        )
        assert status == 200

        # Bob creates a folder
        await requester(
            "POST",
            "/db/guillotina/users/bob/",
            data=json.dumps({"@type": "Folder", "id": "bobfolder"}),
            auth_type="Basic",
            token=bob_token,
        )

        # Alice tries to duplicate the file into Bob's folder
        resp, status = await requester(
            "POST",
            "/db/guillotina/users/bob/foobar1/@duplicate",
            data=json.dumps(
                {
                    "new_id": "foobar-from-alice",
                    "destination": "/users/bob/bobfolder",
                    "check_permission": False,
                }
            ),
            auth_type="Basic",
            token=alice_token,
        )
        assert status == 412
        assert "You do not have permission to add content to the destination object" in resp["message"]

        # Alice tries to move the file into Bob's folder
        resp, status = await requester(
            "POST",
            "/db/guillotina/users/bob/foobar1/@move",
            data=json.dumps(
                {
                    "new_id": "foobar-from-alice",
                    "destination": "/users/bob/bobfolder",
                    "check_permission": False,
                }
            ),
            auth_type="Basic",
            token=alice_token,
        )
        assert status == 412
        assert "You do not have permission to add content to the destination object" in resp["message"]


async def test_create_content_fields(container_requester):
    async with container_requester as requester:
        response, status = await requester(
            "POST",
            "/db/guillotina",
            data=json.dumps(
                {
                    "@type": "Example",
                    "id": "foobar",
                    "categories": [{"label": "foobar", "number": 5}],
                    "textline_field": "foobar",
                    "text_field": "foobar",
                    "dict_value": {"foo": "bar"},
                    "datetime": datetime.utcnow().isoformat(),
                }
            ),
        )
        assert status == 201
        response, status = await requester("GET", "/db/guillotina/foobar")
        assert response["dict_value"]["foo"] == "bar"
        assert len(response["categories"]) == 1
        assert response["textline_field"] == "foobar"
        assert response["text_field"] == "foobar"


async def test_raise_http_exception_works(container_requester):
    async with container_requester as requester:
        _, status = await requester("POST", "/@raise-http-exception")
        assert status == 422
        _, status = await requester("GET", "/@raise-http-exception")
        assert status == 422


async def test_anonymous_user_does_not_get_authenticated_role(container_requester):
    async with container_requester as requester:
        # Make call as anonymous user
        _, status = await requester("GET", "/@myEndpoint", auth_type="Bearer", token="foo")
        assert status == 401


async def test_addable_types(container_requester):
    async with container_requester as requester:
        response, status = await requester("GET", "/db/guillotina/@addable-types")
        assert status == 200
        assert "Item" in response


async def test_not_allowed_to_create_container_inside_container(container_requester):
    """Get a content type definition."""
    async with container_requester as requester:
        _, status = await requester("POST", "/db/guillotina", data=json.dumps({"@type": "Container"}))
        assert status == 412


async def test_get_with_include_omit(container_requester):
    """Get a content type definition."""
    async with container_requester as requester:
        response, _ = await requester(
            "POST", "/db/guillotina", data=json.dumps({"@type": "Item", "id": "foobar"})
        )
        response, _ = await requester("GET", "/db/guillotina/foobar?include=title")
        assert "title" in response
        assert "guillotina.behaviors.dublincore.IDublinCore" not in response

        response, _ = await requester(
            "GET", "/db/guillotina/foobar?omit=guillotina.behaviors.dublincore.IDublinCore"
        )
        assert "title" in response
        assert "guillotina.behaviors.dublincore.IDublinCore" not in response


async def test_return_correct_content_type(container_requester):
    """Get a content type definition."""
    async with container_requester as requester:
        response, _, headers = await requester.make_request(
            "GET", "/db/guillotina", accept="application/json"
        )
        assert "application/json" in headers["Content-Type"]

        response, _, headers = await requester.make_request("GET", "/db/guillotina", accept="text/html,*/*")
        # it will convert it to string with html
        assert "text/html" in headers["Content-Type"]
        assert b"<html" in response


async def test_get_all_permissions(container_requester):
    """Get a content type definition."""
    async with container_requester as requester:
        _, status = await requester("GET", "/db/guillotina/@all_permissions")
        assert status == 200


async def test_patching_write_protected_field_without_permission_should_return_401(container_requester):
    async with container_requester as requester:
        resp, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps(
                {
                    "@type": "Example",
                    "title": "Item1",
                    "id": "item1",
                    "categories": [{"label": "term1", "number": 1.0}, {"label": "term2", "number": 2.0}],
                }
            ),
        )
        assert status == 201

        # Patching write protected field
        _, status = await requester(
            "PATCH", "/db/guillotina/item1", data=json.dumps({"write_protected": "does it work?"})
        )
        assert status == 401


async def test_items_fullobjects(container_requester):
    """Get a content type definition."""
    async with container_requester as requester:
        # add 20 items
        for _ in range(22):
            response, _ = await requester("POST", "/db/guillotina", data=json.dumps({"@type": "Item"}))
        response, _ = await requester("GET", "/db/guillotina/?fullobjects")
        assert len(response["items"]) == 22
        assert "guillotina.behaviors.dublincore.IDublinCore" in response["items"][0]


async def test_items(container_requester):
    """Get a content type definition."""
    async with container_requester as requester:
        # add 20 items
        for _ in range(22):
            response, _ = await requester("POST", "/db/guillotina", data=json.dumps({"@type": "Item"}))
        response, _ = await requester("GET", "/db/guillotina/@items?page_size=10")
        assert len(response["items"]) == 10
        assert response["total"] == 22
        items = [i["@uid"] for i in response["items"]]

        response, _ = await requester("GET", "/db/guillotina/@items?page_size=10&page=2")
        assert len(response["items"]) == 10
        assert response["total"] == 22
        items.extend([i["@uid"] for i in response["items"]])

        response, _ = await requester("GET", "/db/guillotina/@items?page_size=10&page=3")
        assert len(response["items"]) == 2
        items.extend([i["@uid"] for i in response["items"]])

        # we should have 22 unique uids now
        assert len(set(items)) == 22

        response, _ = await requester(
            "GET", "/db/guillotina/@items?omit=guillotina.behaviors.dublincore.IDublinCore"
        )
        item = response["items"][0]
        assert "guillotina.behaviors.dublincore.IDublinCore" not in item

        response, _ = await requester("GET", "/db/guillotina/@items?include=title")
        item = response["items"][0]
        assert "guillotina.behaviors.dublincore.IDublinCore" not in item


async def test_debug_headers(container_requester):
    async with container_requester as requester:
        _, _, headers = await requester.make_request("GET", "/db/guillotina", headers={"X-Debug": "1"})
        assert "XG-Total-Cache-hits" in headers
        assert "XG-Timing-0-Start" in headers


async def test_adapter_exception_handlers(container_requester):
    async with container_requester as requester:
        response, status = await requester("POST", "/db/guillotina", data='{"foobar": "}')  # bug in json
        assert status == 412
        assert response["reason"] == "jsonDecodeError"


async def test_patch_with_payload_again(container_requester):
    async with container_requester as requester:
        response, _ = await requester(
            "POST", "/db/guillotina", data=json.dumps({"@type": "Item", "id": "foobar"})
        )
        response, _ = await requester("GET", "/db/guillotina/foobar")
        assert not response["title"]
        response["title"] = "Foobar"
        await requester("PATCH", f"/db/guillotina/foobar", data=json.dumps(response))
        response, _ = await requester("GET", f"/db/guillotina/foobar")
        assert response["title"] == "Foobar"


async def test_resolveuid(container_requester):
    async with container_requester as requester:
        resp, _ = await requester("POST", "/db/guillotina/", data=json.dumps({"@type": "Item", "id": "item"}))

        uid = resp["@uid"]
        _, status = await requester("GET", f"/db/guillotina/@resolveuid/{uid}", allow_redirects=False)
        assert status == 301


async def test_invalid_resolveuid(container_requester):
    async with container_requester as requester:
        _, status = await requester("GET", f"/db/guillotina/@resolveuid/foobar", allow_redirects=False)
        assert status == 404


async def test_do_not_error_with_invalid_payload(container_requester):
    async with container_requester as requester:
        _, status = await requester(
            "POST", "/db/guillotina/", data=json.dumps({"@type": "Item", "title": "Item1", "id": "item1"})
        )
        assert status == 201
        _, status = await requester(
            "PATCH", "/db/guillotina/item1", data=json.dumps({"foo.bar.blah": "foobar"})
        )
        assert status == 204


async def test_create_content_with_custom_id_does_not_allow_bad_id(container_requester):
    # using custom id generator in test package
    async with container_requester as requester:
        _, status = await requester(
            "POST", "/db/guillotina/", data=json.dumps({"@type": "Item", "bad-id": "sdfkl*&%"})
        )
        assert status == 412


async def test_create_content_with_uses_good_id(container_requester):
    # using custom id generator in test package
    async with container_requester as requester:
        resp, status = await requester(
            "POST", "/db/guillotina/", data=json.dumps({"@type": "Item", "custom-id": "foobar"})
        )
        assert "foobar" == resp["@name"]


async def test_tags_patch_field(container_requester):
    async with container_requester as requester:
        _, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps(
                {
                    "@type": "Item",
                    "title": "Item1",
                    "id": "item1",
                    "@behaviors": [IDublinCore.__identifier__],
                    IDublinCore.__identifier__: {"tags": ["one"]},
                }
            ),
        )
        assert status == 201
        resp, status = await requester(
            "PATCH",
            "/db/guillotina/item1",
            data=json.dumps({IDublinCore.__identifier__: {"tags": {"op": "append", "value": "two"}}}),
        )
        assert status == 204

        resp, status = await requester("GET", "/db/guillotina/item1")
        assert status == 200
        assert resp[IDublinCore.__identifier__]["tags"] == ["one", "two"]

        resp, status = await requester(
            "PATCH",
            "/db/guillotina/item1",
            data=json.dumps({IDublinCore.__identifier__: {"tags": {"op": "appendunique", "value": "two"}}}),
        )
        resp, status = await requester("GET", "/db/guillotina/item1")
        assert resp[IDublinCore.__identifier__]["tags"] == ["one", "two"]

        resp, status = await requester(
            "PATCH",
            "/db/guillotina/item1",
            data=json.dumps(
                {IDublinCore.__identifier__: {"tags": {"op": "extendunique", "value": ["one", "two"]}}}
            ),
        )
        resp, status = await requester("GET", "/db/guillotina/item1")
        assert resp[IDublinCore.__identifier__]["tags"] == ["one", "two"]


async def test_field_values_instance(container_requester):
    async with container_requester as requester:
        await requester(
            "POST", "/db/guillotina/", data=json.dumps({"@type": "Item", "title": "Item1", "id": "item1"})
        )
        resp, status = await requester("GET", "/db/guillotina/item1/@fieldvalue/title")
        assert status == 200
        assert resp == "Item1"


async def test_field_values_behavior(container_requester):
    async with container_requester as requester:
        await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps({"@type": "Item", "id": "item1", IDublinCore.__identifier__: {"tags": ["one"]}}),
        )
        resp, status = await requester(
            "GET", "/db/guillotina/item1/@fieldvalue/{}.tags".format(IDublinCore.__identifier__)
        )
        assert status == 200
        assert resp == ["one"]


async def test_field_values_with_custom_renderer(container_requester):
    async with container_requester as requester:
        _, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps(
                {
                    "@type": "Item",
                    "id": "item1",
                    "@behaviors": [ITestBehavior.__identifier__],
                    ITestBehavior.__identifier__: {
                        "foobar": "blah",
                        "bucket_dict": {
                            "op": "update",
                            "value": [{"key": str(idx), "value": str(idx)} for idx in range(50)],
                        },
                        "test_required_field": "foobar",
                    },
                }
            ),
        )
        assert status == 201
        resp, status = await requester(
            "GET", "/db/guillotina/item1/@fieldvalue/{}.bucket_dict".format(ITestBehavior.__identifier__)
        )
        assert status == 200
        assert resp["values"]
        assert resp["total"] == 50
        assert resp["cursor"] == 1

        resp, status = await requester(
            "GET",
            "/db/guillotina/item1/@fieldvalue/{}.bucket_dict?cursor={}".format(
                ITestBehavior.__identifier__, resp["cursor"]
            ),
        )
        assert status == 200
        assert resp["values"]
        assert resp["cursor"] == 2


async def test_field_values_404(container_requester):
    async with container_requester as requester:
        _, status = await requester(
            "POST", "/db/guillotina/", data=json.dumps({"@type": "Item", "id": "item1"})
        )
        _, status = await requester("GET", "/db/guillotina/item1/@fieldvalue/title")
        assert status == 200
        _, status = await requester("GET", "/db/guillotina/item1/@fieldvalue/foobar")
        assert status == 404
        _, status = await requester("GET", "/db/guillotina/item1/@fieldvalue/foo.bar.wrong")
        assert status == 404
        _, status = await requester(
            "GET", "/db/guillotina/item1/@fieldvalue/{}.foobar".format(IDublinCore.__identifier__)
        )
        assert status == 404
        _, status = await requester(
            "GET", "/db/guillotina/item1/@fieldvalue/{}.size".format(IFile.__identifier__)
        )
        assert status == 404
        _, status = await requester(
            "GET", "/db/guillotina/item1/@fieldvalue/{}.title".format(IResource.__identifier__)
        )
        assert status == 404


async def test_field_values_unauthorized(container_requester):
    async with container_requester as requester:
        _, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps(
                {
                    "@type": "Item",
                    "id": "item1",
                    "@behaviors": [ITestBehavior.__identifier__],
                    ITestBehavior.__identifier__: {
                        "foobar": "blah",
                        "no_read_field": "foobar",
                        "test_required_field": "foobar",
                    },
                }
            ),
        )
        assert status == 201
        _, status = await requester(
            "GET", "/db/guillotina/item1/@fieldvalue/{}.no_read_field".format(ITestBehavior.__identifier__)
        )
        assert status == 401


async def test_field_values_dict_bucket_preconditions(container_requester):
    async with container_requester as requester:
        _, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps({"@type": "Item", "id": "item1", "@behaviors": [ITestBehavior.__identifier__]}),
        )
        assert status == 201
        resp, status = await requester(
            "GET", "/db/guillotina/item1/@fieldvalue/{}.bucket_dict".format(ITestBehavior.__identifier__)
        )
        assert status == 200
        assert len(resp["values"]) == 0
        assert resp["cursor"] is None
        assert resp["total"] == 0

        await requester(
            "PATCH",
            "/db/guillotina/item1",
            data=json.dumps(
                {
                    "@behaviors": [ITestBehavior.__identifier__],
                    ITestBehavior.__identifier__: {
                        "foobar": "blah",
                        "bucket_dict": {
                            "op": "update",
                            "value": [{"key": str(idx), "value": str(idx)} for idx in range(20)],
                        },
                        "test_required_field": "foobar",
                    },
                }
            ),
        )
        resp, status = await requester(
            "GET", "/db/guillotina/item1/@fieldvalue/{}.bucket_dict".format(ITestBehavior.__identifier__)
        )
        assert status == 200
        assert resp["values"]
        assert resp["total"] == 20
        assert resp["cursor"] == 1

        _, status = await requester(
            "GET",
            "/db/guillotina/item1/@fieldvalue/{}.bucket_dict?cursor=foobar".format(
                ITestBehavior.__identifier__
            ),
        )
        assert status == 412

        _, status = await requester(
            "GET",
            "/db/guillotina/item1/@fieldvalue/{}.bucket_dict?cursor=500".format(ITestBehavior.__identifier__),
        )
        assert status == 412

        # delete annotation for bucket that should be there, we should get 410
        root = await utils.get_root(db=requester.db)
        async with transaction(db=requester.db):
            container = await root.async_get("guillotina")
            obj = await container.async_get("item1")
            beh = await get_behavior(obj, ITestBehavior)
            val = beh.bucket_dict
            ann_name = val.get_annotation_name(val.buckets[0]["id"])
            annotations_container = IAnnotations(obj)
            await annotations_container.async_del(ann_name)

        _, status = await requester(
            "GET", "/db/guillotina/item1/@fieldvalue/{}.bucket_dict".format(ITestBehavior.__identifier__)
        )
        assert status == 410


async def test_field_values_list_bucket(container_requester):
    async with container_requester as requester:
        _, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps({"@type": "Item", "id": "item1", "@behaviors": [ITestBehavior.__identifier__]}),
        )
        assert status == 201
        resp, status = await requester(
            "GET", "/db/guillotina/item1/@fieldvalue/{}.bucket_list".format(ITestBehavior.__identifier__)
        )
        assert status == 200
        assert len(resp["values"]) == 0
        assert resp["cursor"] is None
        assert resp["total"] == 0

        await requester(
            "PATCH",
            "/db/guillotina/item1",
            data=json.dumps(
                {
                    "@behaviors": [ITestBehavior.__identifier__],
                    ITestBehavior.__identifier__: {
                        "foobar": "blah",
                        "bucket_list": {"op": "extend", "value": [str(idx) for idx in range(20)]},
                        "test_required_field": "foobar",
                    },
                }
            ),
        )
        resp, status = await requester(
            "GET", "/db/guillotina/item1/@fieldvalue/{}.bucket_list".format(ITestBehavior.__identifier__)
        )
        assert status == 200
        assert len(resp["values"]) == 10
        assert resp["total"] == 20
        assert resp["cursor"] == 1

        resp, status = await requester(
            "GET",
            "/db/guillotina/item1/@fieldvalue/{}.bucket_list?cursor=1".format(ITestBehavior.__identifier__),
        )
        assert status == 200
        assert len(resp["values"]) == 10
        assert resp["cursor"] == 2

        resp, status = await requester(
            "GET",
            "/db/guillotina/item1/@fieldvalue/{}.bucket_list?cursor=4".format(ITestBehavior.__identifier__),
        )
        assert status == 410

        _, status = await requester(
            "GET",
            "/db/guillotina/item1/@fieldvalue/{}.bucket_list?cursor=foobar".format(
                ITestBehavior.__identifier__
            ),
        )
        assert status == 412

        _, status = await requester(
            "GET",
            "/db/guillotina/item1/@fieldvalue/{}.bucket_list?cursor=500".format(ITestBehavior.__identifier__),
        )
        assert status == 410


async def test_patch_field_validation(container_requester):
    async with container_requester as requester:
        _, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps({"@type": "Item", IDublinCore.__identifier__: {"tags": 1}}),
        )
        assert status == 412
        _, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps({"@type": "Item", IDublinCore.__identifier__: {"tags": [1]}}),
        )
        assert status == 201


async def test_move_with_already_existing_id(container_requester):
    async with container_requester as requester:
        await requester("POST", "/db/guillotina/", data=json.dumps({"@type": "Folder", "id": "container1"}))
        await requester("POST", "/db/guillotina/", data=json.dumps({"@type": "Folder", "id": "container2"}))
        await requester(
            "POST", "/db/guillotina/container1", data=json.dumps({"@type": "Item", "id": "foobar"})
        )
        await requester(
            "POST", "/db/guillotina/container2", data=json.dumps({"@type": "Item", "id": "foobar"})
        )
        _, status = await requester(
            "POST",
            "/db/guillotina/container1/foobar/@move",
            data=json.dumps({"destination": "/container2", "new_id": "foobar"}),
        )
        assert status == 409


async def test_move_with_bad_id(container_requester):
    async with container_requester as requester:
        await requester("POST", "/db/guillotina/", data=json.dumps({"@type": "Folder", "id": "container1"}))
        await requester("POST", "/db/guillotina/", data=json.dumps({"@type": "Folder", "id": "container2"}))
        await requester(
            "POST", "/db/guillotina/container1", data=json.dumps({"@type": "Item", "id": "foobar"})
        )
        _, status = await requester(
            "POST",
            "/db/guillotina/container1/foobar/@move",
            data=json.dumps({"destination": "/container2", "new_id": "sdfkl*&%"}),
        )
        assert status == 412


@pytest.mark.app_settings(DBUSERS_DEFAULT_SETTINGS)
async def test_duplicate_with_reset_acl(dbusers_requester):
    async with dbusers_requester as requester:
        # Add Bob user
        _, status = await requester(
            "POST",
            "/db/guillotina/users",
            data=json.dumps(
                {
                    "@type": "User",
                    "name": "Bob",
                    "id": "bob",
                    "username": "bob",
                    "email": "bob@foo.com",
                    "password": "bob",
                }
            ),
        )
        assert status == 201

        # Add Alice user
        _, status = await requester(
            "POST",
            "/db/guillotina/users",
            data=json.dumps(
                {
                    "@type": "User",
                    "name": "Alice",
                    "id": "alice",
                    "username": "alice",
                    "email": "alice@foo.com",
                    "password": "alice",
                }
            ),
        )
        assert status == 201

        bob_token = base64.b64encode(b"bob:bob").decode("ascii")
        alice_token = base64.b64encode(b"alice:alice").decode("ascii")

        # Bob creates a file in its folder
        _, status = await requester(
            "POST",
            "/db/guillotina/users/bob/",
            data=json.dumps({"@type": "Item", "id": "foobar1"}),
            auth_type="Basic",
            token=bob_token,
        )
        assert status == 201

        # Shares it with alice as manager
        _, status = await requester(
            "POST",
            "/db/guillotina/users/bob/foobar1/@sharing",
            data=json.dumps(
                {"prinrole": [{"principal": "alice", "role": "guillotina.Owner", "setting": "Allow"}]}
            ),
            auth_type="Basic",
            token=bob_token,
        )
        assert status == 200

        # Aice creates a folder
        await requester(
            "POST",
            "/db/guillotina/users/alice/",
            data=json.dumps({"@type": "Folder", "id": "alicefolder"}),
            auth_type="Basic",
            token=alice_token,
        )
        assert status == 200

        # Alice duplicates the file into her folder
        _, status = await requester(
            "POST",
            "/db/guillotina/users/bob/foobar1/@duplicate",
            data=json.dumps(
                {
                    "new_id": "foobar-from-alice",
                    "destination": "/users/alice",
                    "check_permission": False,
                    "reset_acl": True,
                }
            ),
            auth_type="Basic",
            token=alice_token,
        )
        assert status == 200

        # check creators and contributors on duplicated file
        resp, status = await requester("GET", "/db/guillotina/users/alice/foobar-from-alice")
        assert status == 200
        assert resp["guillotina.behaviors.dublincore.IDublinCore"]["creators"] == ["alice"]
        assert resp["guillotina.behaviors.dublincore.IDublinCore"]["contributors"] == ["alice"]
        # check owner role
        resp, status = await requester("GET", "/db/guillotina/users/alice/foobar-from-alice/@sharing")
        assert status == 200
        assert len(resp["local"]["prinrole"].keys()) == 1
        assert resp["local"]["prinrole"]["alice"] == {"guillotina.Owner": "Allow"}


async def test_required_field_work_with_none(container_requester):
    async with container_requester as requester:
        _, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps(
                {
                    "@type": "Item",
                    "@behaviors": [ITestBehavior.__identifier__],
                    ITestBehavior.__identifier__: {},
                }
            ),
        )
        assert status == 412

        _, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps(
                {
                    "@type": "Item",
                    "@behaviors": [ITestBehavior.__identifier__],
                    ITestBehavior.__identifier__: {"test_required_field": None},
                }
            ),
        )
        assert status == 412

        _, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps(
                {
                    "@type": "Item",
                    "id": "foobar",
                    "@behaviors": [ITestBehavior.__identifier__],
                    ITestBehavior.__identifier__: {"test_required_field": "Foobar"},
                }
            ),
        )
        assert status == 201

        _, status = await requester(
            "PATCH",
            "/db/guillotina/foobar",
            data=json.dumps({ITestBehavior.__identifier__: {"test_required_field": None}}),
        )
        assert status == 412


async def test_json_schema_query_params(container_requester):
    async with container_requester as requester:
        # JSON schema validation
        resp, status = await requester("GET", "/@json-schema-validation")
        assert status == 412
        assert resp["parameter"] == "foo"

        resp, status = await requester("GET", "/@json-schema-validation?foo=blah")
        assert status == 412
        assert resp["parameter"] == "foo"
        assert resp["validator_value"] == "number"

        resp, status = await requester("GET", "/@json-schema-validation?foo=5")
        assert status == 200

        resp, status = await requester("GET", "/@json-schema-validation?foo=5.5")
        assert status == 200


async def test_handle_none_value_for_behavior(container_requester):
    async with container_requester as requester:
        _, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps(
                {
                    "@type": "Item",
                    "title": "Item1",
                    "id": "item1",
                    "@behaviors": [IDublinCore.__identifier__],
                    IDublinCore.__identifier__: None,
                }
            ),
        )
        assert status == 201


async def test_default_post_and_patch_handles_wrong_json_payload(container_requester):
    async with container_requester as requester:
        _, status = await requester("POST", "/db/guillotina/", data=json.dumps("foobar"))
        assert status == 412

        _, status = await requester("PATCH", "/db/guillotina/", data=json.dumps("foobar"))
        assert status == 412


@pytest.mark.app_settings({"max_content_depth": 2})
async def test_max_depth_on_post(container_requester):
    async with container_requester as requester:
        _, status = await requester(
            "POST", "/db/guillotina/", data=json.dumps({"@type": "Folder", "id": "foo"})
        )
        assert status == 201
        _, status = await requester(
            "POST", "/db/guillotina/foo", data=json.dumps({"@type": "Folder", "id": "foo"})
        )
        assert status == 201
        resp, status = await requester(
            "POST", "/db/guillotina/foo/foo", data=json.dumps({"@type": "Folder", "id": "foo"})
        )
        assert status == 412
        assert resp["reason"] == "preconditionFailed"
        assert resp["type"] == "MaxDepthReached"
