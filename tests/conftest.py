import types
from typing import Any, Dict, Iterable, List, NamedTuple, Tuple

import pytest
import yaml
from aiohttp import hdrs, web
from aiohttp.test_utils import TestServer
from aiohttp.web_request import Request

from s2ctl import config as config_module
from s2ctl.entrypoint import entry_point
from ssclient.http_client import HttpClient
from ssclient.task_entities import TaskState
from ssclient.task_wait import TASK_TIMEOUT_SECS

TEST_SERVER_PORT = 65182

_CONFIG_OPTION_NAME = 'config_manager'
_ISOLATED_KEYRING_KEY = 'test-keyring-key'


@pytest.fixture(autouse=True)
def cli_config(tmp_path, monkeypatch):
    """Конфиг и keyring CLI в tmp_path вместо домашнего каталога того, кто запускает тесты.

    Подменяется default самого объекта параметра click, а не константа модуля config:
    default зашит в параметр в момент импорта entry_point, а команды в тестах
    вызываются без --config.
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


@pytest.fixture(autouse=True)
def task_timeout_of_invocation():
    """Таймаут ожидания задачи живёт в контексте вызова CLI.

    Значение `--timeout`, поставленное одним тестом, иначе досталось бы следующим:
    прогон идёт в одном процессе и одном контексте.
    """
    token = TASK_TIMEOUT_SECS.set(None)

    yield

    TASK_TIMEOUT_SECS.reset(token)


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


class FakeRequest(NamedTuple):
    """Запрос, который сервис отправил через порт HTTP."""

    method: str
    path: str
    payload: Any = None


class FakeHttpClient(object):
    """Заглушка HttpClientPort: ответы задаются парой (метод, путь), запросы записываются.

    Последний заданный ответ повторяется — так задача «висит» в незавершённом статусе
    сколько угодно опросов. Запрос по незаданной паре — ошибка теста: сервис пошёл не туда.
    """

    def __init__(self) -> None:
        self.requests: List[FakeRequest] = []
        self._responses: Dict[Tuple[str, str], List[Any]] = {}

    def on(self, method: str, path: str, *responses: Any) -> 'FakeHttpClient':
        self._responses[(method, path)] = list(responses)
        return self

    def paths(self, method: str) -> List[str]:
        return [request.path for request in self.requests if request.method == method]

    async def get(self, path: str) -> Any:
        return self._respond(hdrs.METH_GET, path)

    async def post(self, path: str, payload: Any = None) -> Any:
        return self._respond(hdrs.METH_POST, path, payload)

    async def put(self, path: str, payload: Any = None) -> Any:
        return self._respond(hdrs.METH_PUT, path, payload)

    async def patch(self, path: str, payload: Any = None) -> Any:
        return self._respond(hdrs.METH_PATCH, path, payload)

    async def delete(self, path: str) -> Any:
        return self._respond(hdrs.METH_DELETE, path)

    def _respond(self, method: str, path: str, payload: Any = None) -> Any:
        self.requests.append(FakeRequest(method, path, payload))
        responses = self._responses.get((method, path))
        if responses is None:
            raise AssertionError(
                'сервис обратился по незаданному маршруту: {method} {path}'.format(
                    method=method, path=path,
                ),
            )
        if len(responses) > 1:
            return responses.pop(0)
        return responses[0]


def task_response(
    task_id: str,
    state: TaskState,
    resources: Iterable[Tuple[str, str]] = (),
) -> Dict[str, Any]:
    """Тело ответа publisher'а на чтение задачи: статус строкой, ресурсы парами (тип, id)."""
    return {
        'task': {
            'id': task_id,
            'is_completed': state.value,
            'resources': [
                {'type': resource_type, 'id': resource_id}
                for resource_type, resource_id in resources
            ],
        },
    }


@pytest.fixture
def fake_http_client():
    return FakeHttpClient()
