from async_asgi_testclient import TestClient
from guillotina import task_vars
from guillotina import testing
from guillotina.component import get_utility
from guillotina.component import globalregistry
from guillotina.const import ROOT_ID
from guillotina.const import TRASHED_ID
from guillotina.db.interfaces import IPostgresStorage
from guillotina.factory import make_app
from guillotina.interfaces import IApplication
from guillotina.interfaces import IDatabase
from guillotina.tests import mocks
from guillotina.tests.utils import ContainerRequesterAsyncContextManager
from guillotina.tests.utils import get_mocked_request
from guillotina.tests.utils import login
from guillotina.tests.utils import logout
from guillotina.tests.utils import wrap_request
from guillotina.transactions import get_tm
from guillotina.transactions import transaction
from guillotina.utils import merge_dicts
from unittest import mock

import aiohttp
import asyncio
import json
import os
import pytest


_dir = os.path.dirname(os.path.realpath(__file__))

DATABASE = os.environ.get("DATABASE", "DUMMY")
DB_SCHEMA = os.environ.get("DB_SCHEMA", "public")

annotations = {"testdatabase": DATABASE, "test_dbschema": DB_SCHEMA, "redis": None}


def base_settings_configurator(settings):
    settings["load_utilities"]["catalog"] = {
        "provides": "guillotina.interfaces.ICatalogUtility",
        "factory": "guillotina.catalog.catalog.DefaultSearchUtility",
    }


testing.configure_with(base_settings_configurator)


@pytest.yield_fixture
def event_loop():
    """Create an instance of the default event loop for each test case."""
    # https://github.com/pytest-dev/pytest-asyncio/issues/30#issuecomment-226947196
    policy = asyncio.get_event_loop_policy()
    res = policy.new_event_loop()
    asyncio.set_event_loop(res)
    res._close = res.close
    res.close = lambda: None

    yield res

    res._close()


def get_dummy_settings(pytest_node=None):
    settings = testing.get_settings()
    settings["databases"]["db"]["storage"] = "DUMMY"
    settings["databases"]["db"]["dsn"] = {}
    settings = _update_from_pytest_markers(settings, pytest_node)
    return settings


def configure_db(
    obj,
    scheme="postgres",
    dbname="guillotina",
    user="postgres",
    host="localhost",
    port=5432,
    password="",
    storage="postgresql",
):
    obj.update({"storage": storage, "partition": "guillotina.interfaces.IResource"})
    obj["dsn"] = {
        "scheme": scheme,
        "dbname": dbname,
        "user": user,
        "host": host,
        "port": port,
        "password": password,
    }


def _update_from_pytest_markers(settings, pytest_node):
    if not pytest_node:
        return settings

    # Update test app settings from pytest markers
    marks = []
    try:
        marks.extend([mark for mark in pytest_node.iter_markers(name="app_settings")])
    except AttributeError:
        # Older pytest versions
        mark = pytest_node.get_marker("app_settings")
        if mark is not None:
            marks.append(mark)

    for mark in marks:
        to_update = mark.args[0]
        settings = merge_dicts(settings, to_update)

    return settings


def get_db_settings(pytest_node=None):
    settings = testing.get_settings()
    if annotations["redis"] is not None:
        if "redis" not in settings:
            settings["redis"] = {}
        settings["redis"]["host"] = annotations["redis"][0]
        settings["redis"]["port"] = annotations["redis"][1]

    if annotations["testdatabase"] == "DUMMY":
        return _update_from_pytest_markers(settings, pytest_node)

    settings["databases"]["db"]["storage"] = "postgresql"
    settings["databases"]["db"]["db_schema"] = annotations["test_dbschema"]

    settings["databases"]["db"]["dsn"] = {
        "scheme": "postgres",
        "dbname": annotations.get("pg_db", "guillotina"),
        "user": "postgres",
        "host": annotations.get("pg_host", "localhost"),
        "port": annotations.get("pg_port", 5432),
        "password": "",
    }

    options = dict(
        host=annotations.get("pg_host", "localhost"),
        port=annotations.get("pg_port", 5432),
        dbname=annotations.get("pg_db", "guillotina"),
    )
    settings = _update_from_pytest_markers(settings, pytest_node)

    configure_db(settings["databases"]["db"], **options)
    configure_db(settings["databases"]["db-custom"], **options)
    configure_db(settings["storages"]["db"], **options)

    return settings


@pytest.fixture(scope="session")
def db():
    if annotations["testdatabase"] == "DUMMY":
        yield
    else:
        import pytest_docker_fixtures

        host, port = pytest_docker_fixtures.pg_image.run()

        annotations["pg_host"] = host
        annotations["pg_port"] = port

        yield host, port  # provide the fixture value

        pytest_docker_fixtures.pg_image.stop()


class GuillotinaDBAsgiRequester(object):
    def __init__(self, client):
        self.client = client
        self.root = get_utility(IApplication, name="root")
        self.db = self.root["db"]

    async def __call__(
        self,
        method,
        path,
        params=None,
        data=None,
        authenticated=True,
        auth_type="Basic",
        headers={},
        cookies={},
        token=testing.ADMIN_TOKEN,
        accept="application/json",
        allow_redirects=True,
    ):

        value, status, _ = await self.make_request(
            method,
            path,
            params=params,
            data=data,
            authenticated=authenticated,
            auth_type=auth_type,
            headers=headers,
            cookies=cookies,
            token=token,
            accept=accept,
            allow_redirects=allow_redirects,
        )
        return value, status

    async def make_request(
        self,
        method,
        path,
        params=None,
        data=None,
        authenticated=True,
        auth_type="Basic",
        headers={},
        cookies={},
        token=testing.ADMIN_TOKEN,
        accept="application/json",
        allow_redirects=True,
    ):
        settings = {}
        headers = headers.copy()
        settings["headers"] = headers
        if accept is not None:
            settings["headers"]["ACCEPT"] = accept
        if authenticated and token is not None:
            settings["headers"]["AUTHORIZATION"] = "{} {}".format(auth_type, token)

        settings["query_string"] = params
        settings["data"] = data
        settings["allow_redirects"] = allow_redirects
        settings["cookies"] = cookies

        operation = getattr(self.client, method.lower(), None)
        resp = await operation(path, **settings)
        if "Content-Range" in resp.headers:
            value = resp.content
        else:
            try:
                value = resp.json()
            except json.decoder.JSONDecodeError:
                value = resp.content

        status = resp.status_code
        return value, status, resp.headers

    def transaction(self, request=None):
        if request is None:
            request = get_mocked_request(db=self.db)
        login()
        return wrap_request(request, transaction(db=self.db, adopt_parent_txn=True))

    async def close(self):
        pass


class GuillotinaDBHttpRequester(object):
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.client = aiohttp.ClientSession()
        self.root = get_utility(IApplication, name="root")
        self.db = self.root["db"]

    async def __call__(
        self,
        method,
        path,
        params=None,
        data=None,
        authenticated=True,
        auth_type="Basic",
        headers=None,
        token=testing.ADMIN_TOKEN,
        accept="application/json",
        allow_redirects=True,
    ):

        value, status, _ = await self.make_request(
            method,
            path,
            params=params,
            data=data,
            authenticated=authenticated,
            auth_type=auth_type,
            headers=headers,
            token=token,
            accept=accept,
            allow_redirects=allow_redirects,
        )
        return value, status

    async def make_request(
        self,
        method,
        path,
        params=None,
        data=None,
        authenticated=True,
        auth_type="Basic",
        headers=None,
        token=testing.ADMIN_TOKEN,
        accept="application/json",
        allow_redirects=True,
    ):
        if headers is None:
            headers = {}
        settings = {}
        headers = headers.copy()
        settings["headers"] = headers
        if accept is not None:
            settings["headers"]["ACCEPT"] = accept
        if authenticated and token is not None:
            settings["headers"]["AUTHORIZATION"] = "{} {}".format(auth_type, token)

        settings["params"] = params
        settings["data"] = data
        settings["allow_redirects"] = allow_redirects

        async with aiohttp.ClientSession() as session:
            operation = getattr(session, method.lower(), None)
            async with operation(self.make_url(path), **settings) as resp:
                try:
                    value = await resp.json()
                except aiohttp.client_exceptions.ContentTypeError:
                    value = await resp.read()

                status = resp.status
                return value, status, resp.headers

    def transaction(self, request=None):
        if request is None:
            request = get_mocked_request(db=self.db)
        login()
        return wrap_request(request, transaction(db=self.db, adopt_parent_txn=True))

    def make_url(self, path):
        return f"http://{self.host}:{self.port}{path}"

    async def close(self):
        if not self.client.closed:
            await self.client.close()


def clear_task_vars():
    for var in (
        "request",
        "txn",
        "tm",
        "futures",
        "authenticated_user",
        "security_policies",
        "container",
        "registry",
        "db",
    ):
        getattr(task_vars, var).set(None)


@pytest.fixture(scope="function")
async def dummy_guillotina(event_loop, request):
    globalregistry.reset()
    app = make_app(settings=get_dummy_settings(request.node), loop=event_loop)
    async with TestClient(app):
        yield app
    logout()
    clear_task_vars()


class DummyRequestAsyncContextManager(object):
    def __init__(self, dummy_request, loop):
        self.request = dummy_request
        self.loop = loop

    async def __aenter__(self):
        task = asyncio.Task.current_task(loop=self.loop)
        if task is not None:
            task.request = self.request
        return self.request

    async def __aexit__(self, exc_type, exc, tb):
        task = asyncio.Task.current_task(loop=self.loop)
        del task.request


@pytest.fixture(scope="function")
def dummy_request(dummy_guillotina, monkeypatch):
    from guillotina.interfaces import IApplication
    from guillotina.component import get_utility

    root = get_utility(IApplication, name="root")
    db = root["db"]

    request = get_mocked_request(db=db)
    task_vars.request.set(request)
    return request


class RootAsyncContextManager:
    def __init__(self, request):
        self.request = request
        self.root = None
        self.txn = None

    async def __aenter__(self):
        tm = get_tm()
        self.txn = await tm.begin()
        self.root = await tm.get_root()
        return self.root

    async def __aexit__(self, exc_type, exc, tb):
        await self.txn.abort()


@pytest.fixture(scope="function")
async def dummy_txn_root(dummy_request):
    return RootAsyncContextManager(dummy_request)


@pytest.fixture(scope="function")
def mock_txn():
    txn = mocks.MockTransaction()
    task_vars.txn.set(txn)
    yield txn
    task_vars.txn.set(None)


async def _clear_dbs(root):
    # make sure to completely clear db before carrying on...
    for _, db in root:
        if not IDatabase.providedBy(db):
            continue
        storage = db.storage
        if IPostgresStorage.providedBy(storage):
            async with storage.pool.acquire() as conn:
                await conn.execute(
                    """
DELETE from {}
WHERE zoid != '{}' AND zoid != '{}'
""".format(
                        storage._objects_table_name, ROOT_ID, TRASHED_ID
                    )
                )
                await conn.execute(
                    """
SELECT 'DROP INDEX ' || string_agg(indexrelid::regclass::text, ', ')
   FROM   pg_index  i
   LEFT   JOIN pg_depend d ON d.objid = i.indexrelid
                          AND d.deptype = 'i'
   WHERE  i.indrelid = '{}'::regclass
   AND    d.objid IS NULL
""".format(
                        storage._objects_table_name
                    )
                )


@pytest.fixture(scope="function")
async def app(event_loop, db, request):
    globalregistry.reset()
    settings = get_db_settings(request.node)
    app = make_app(settings=settings, loop=event_loop)

    server_settings = settings.get("test_server_settings", {})
    host = server_settings.get("host", "127.0.0.1")
    port = int(server_settings.get("port", 8000))

    from uvicorn import Config, Server

    config = Config(app, host=host, port=port, lifespan="on")
    server = Server(config=config)
    task = asyncio.ensure_future(server.serve(), loop=event_loop)

    while app.app is None and not task.done():
        # Wait for app initialization
        await asyncio.sleep(0.05)

    if task.done():
        task.result()

    await _clear_dbs(app.app.root)

    yield host, port

    server.should_exit = True
    await asyncio.sleep(1)  # There is no other way to wait for server shutdown
    clear_task_vars()


@pytest.fixture(scope="function")
async def app_client(event_loop, db, request):
    globalregistry.reset()
    app = make_app(settings=get_db_settings(request.node), loop=event_loop)
    async with TestClient(app, timeout=30) as client:
        await _clear_dbs(app.app.root)
        yield app, client
    clear_task_vars()


@pytest.fixture(scope="function")
async def guillotina_main(app_client):
    app, _ = app_client
    return app


@pytest.fixture(scope="function")
async def guillotina(app_client):
    _, client = app_client
    return GuillotinaDBAsgiRequester(client)


@pytest.fixture(scope="function")
def guillotina_server(app):
    host, port = app
    return GuillotinaDBHttpRequester(host, port)


@pytest.fixture(scope="function")
def container_requester(guillotina):
    return ContainerRequesterAsyncContextManager(guillotina)


@pytest.fixture(scope="function")
def container_install_requester(guillotina, install_addons):
    return ContainerRequesterAsyncContextManager(guillotina, install_addons)


@pytest.fixture(scope="function")
def container_requester_server(guillotina_server):
    return ContainerRequesterAsyncContextManager(guillotina_server)


async def _bomb_shelter(future, timeout=2):
    try:
        return await asyncio.shield(asyncio.wait_for(future, timeout))
    except asyncio.TimeoutError:
        pass

@pytest.fixture(scope="function")
def command_arguments():
    arguments = mock.MagicMock()
    arguments.line_profiler = False
    arguments.monitor = False
    arguments.profile = False
    return arguments


@pytest.fixture(scope="function")
def container_command(db):
    import psycopg2  # type: ignore

    settings = get_db_settings()
    host = settings["databases"]["db"]["dsn"]["host"]
    port = settings["databases"]["db"]["dsn"]["port"]
    conn = psycopg2.connect(f"dbname=guillotina user=postgres host={host} port={port}")
    cur = conn.cursor()
    cur.execute(open(os.path.join(_dir, "data/tables.sql"), "r").read())
    cur.execute("COMMIT;")
    cur.close()
    conn.close()
    yield {"settings": settings}

    conn = psycopg2.connect(f"dbname=guillotina user=postgres host={host} port={port}")
    cur = conn.cursor()
    cur.execute(
        """
DELETE FROM objects;
DELETe FROM blobs;
COMMIT;"""
    )


@pytest.fixture(scope="session")
def redis_container():
    import pytest_docker_fixtures

    host, port = pytest_docker_fixtures.redis_image.run()
    annotations["redis"] = (host, port)
    yield host, port  # provide the fixture value
    pytest_docker_fixtures.redis_image.stop()
    annotations["redis"] = None


@pytest.fixture(scope="function")
async def dbusers_requester(guillotina):
    return ContainerRequesterAsyncContextManager(guillotina, ["dbusers"])
