import types

import pytest
import yaml
from aiohttp import hdrs, web
from aiohttp.test_utils import TestServer
from aiohttp.web_request import Request

from s2ctl import config as config_module
from s2ctl.entrypoint import entry_point
from ssclient.http_client import HttpClient

TEST_SERVER_PORT = 65182

_CONFIG_OPTION_NAME = 'config_manager'
_ISOLATED_KEYRING_KEY = 'test-keyring-key'


@pytest.fixture(autouse=True)
def cli_config(tmp_path, monkeypatch):
    """Конфиг и keyring CLI в tmp_path вместо домашнего каталога того, кто запускает тесты.

    Подменяется default самого объекта параметра click, а не константа модуля config:
    default зашит в параметр в момент импорта entry_point. Передать путь аргументом
    --config нельзя — опция объявлена как click.types.Path() без path_type, отдаёт str,
    а ConfigManager ждёт Path и падает AttributeError (дефект src, не тестов).
    Переменные S2CTL_* снимаются: их значение в окружении разработчика меняет исход команд.
    """
    config_path = tmp_path / 'config.yaml'
    isolated_config = {
        'keyring': str(tmp_path / 'keyring.cfg'),
        'keyring_key': _ISOLATED_KEYRING_KEY,
        'contexts': [],
        'current_context': '',
    }
    with open(config_path, 'w') as config_file:
        yaml.dump(isolated_config, config_file)

    monkeypatch.setattr(config_module, 'DEFAULT_CONFIG_DIR', tmp_path)
    monkeypatch.setattr(config_module, 'DEFAULT_CONFIG_PATH', config_path)
    monkeypatch.setattr(config_module, 'DEFAULT_CONFIG', types.MappingProxyType(isolated_config))
    for param in entry_point.params:
        if param.name == _CONFIG_OPTION_NAME:
            monkeypatch.setattr(param, 'default', config_path)

    monkeypatch.delenv('S2CTL_CONTEXT_KEY', raising=False)
    monkeypatch.delenv('S2CTL_APIKEY', raising=False)
    monkeypatch.setenv('HOME', str(tmp_path))

    return config_path


async def _server_handelr(request: Request):
    return web.json_response(
        data={
            'headers': dict(request.headers),
            'method': request.method,
            'path': request.path,
            'payload': await (request.json() if request.can_read_body else request.text()),
        }
    )


async def _server_error_handelr(request: Request):
    return web.json_response(
        data={
            'headers': dict(request.headers),
            'method': request.method,
            'path': request.path,
            'payload': await (request.json() if request.can_read_body else request.text()),
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
    return str(http_server.make_url('/'))


@pytest.fixture
def http_client(server_root):
    def factory(apikey):
        return HttpClient(host=server_root, apikey=apikey)

    return factory
