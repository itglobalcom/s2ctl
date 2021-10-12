import pytest
from aiohttp import hdrs, web
from aiohttp.test_utils import TestServer
from aiohttp.web_request import Request

from ssclient.http_client import HttpClient

TEST_SERVER_PORT = 65182


async def _server_handelr(request: Request):
    return web.json_response(
        data={
            'headers': dict(request.headers),
            'method': request.method,
            'path': request.path,
            'payload': await (request.json() if request.has_body else request.text()),
        }
    )


async def _server_error_handelr(request: Request):
    return web.json_response(
        data={
            'headers': dict(request.headers),
            'method': request.method,
            'path': request.path,
            'payload': await (request.json() if request.has_body else request.text()),
        },
        status=int(request.match_info['status']),
    )


@pytest.fixture
async def http_server(aiohttp_server):
    app = web.Application()
    app.router.add_route(hdrs.METH_ANY, '/error/{status}', _server_error_handelr)
    app.router.add_route(hdrs.METH_ANY, '/{any}', _server_handelr)
    app.router.add_route(hdrs.METH_ANY, '/{any}/{another_part}', _server_handelr)
    server = await aiohttp_server(app, port=TEST_SERVER_PORT)

    async with server:
        yield server


@pytest.fixture
def server_root(http_server: TestServer):
    return str(http_server._root)


@pytest.fixture
def http_client(server_root):
    def factory(apikey):
        return HttpClient(host=server_root, apikey=apikey)

    return factory
