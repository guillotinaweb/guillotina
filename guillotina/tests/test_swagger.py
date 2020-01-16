from openapi_spec_validator import validate_v3_spec

import json
import os
import pytest


SWAGGER_SETTINGS = {"applications": ["guillotina.contrib.swagger"]}


@pytest.mark.app_settings(SWAGGER_SETTINGS)
async def test_get_swagger_definition(container_requester):
    async with container_requester as requester:
        resp, status = await requester("GET", "/@swagger")
        assert status == 200
        assert "/" in resp["paths"]

    async with container_requester as requester:
        resp, status = await requester("GET", "/db/@swagger")
        assert status == 200
        assert "/db" in resp["paths"]

    async with container_requester as requester:
        resp, status = await requester("GET", "/db/guillotina/@swagger")
        assert status == 200
        assert "/db/guillotina" in resp["paths"]


@pytest.mark.app_settings(SWAGGER_SETTINGS)
async def test_get_swagger_index(container_requester):
    async with container_requester as requester:
        resp, status = await requester("GET", "/@docs")
        assert status == 200


@pytest.mark.app_settings(SWAGGER_SETTINGS)
async def test_validate_swagger_definition(container_requester):
    async with container_requester as requester:
        await requester("POST", "/db/guillotina", data=json.dumps({"@type": "Folder", "id": "folder"}))
        await requester("POST", "/db/guillotina", data=json.dumps({"@type": "Item", "id": "item"}))
        for path in ("/", "/db", "/db/guillotina", "/db/guillotina/folder", "/db/guillotina/item"):
            resp, status = await requester("GET", os.path.join(path, "@swagger"))
            assert status == 200
            validate_v3_spec(resp)
