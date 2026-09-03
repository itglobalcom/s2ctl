"""Отказ API на команде нового раздела: читаемое сообщение и ненулевой код возврата.

Путь ошибок в CLI общий (`_check_http_response_error` в `s2ctl/click.py`), но проверяется
он на уровне команды: заглушка API отвечает статусом и телом, а тест смотрит на то,
что увидит пользователь, — сообщение вместо traceback.
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
import yaml
from click.testing import CliRunner

from s2ctl.entrypoint import entry_point

APIKEY = '02deadbeef'

FORBIDDEN = 403
NOT_FOUND = 404

# По команде чтения из каждого нового раздела: шлюзы, affinity-группы, VMware.
COMMANDS = (
    ('gateway', 'get', 'l1e2'),
    ('affinity-group', 'get', 'l1g2'),
    ('vmware', 'server', 'get', '100'),
)
COMMAND_IDS = tuple(command[0] for command in COMMANDS)


class ApiStub(object):
    """Ответ Public API, заданный тестом: один и тот же на любой маршрут."""

    def __init__(self) -> None:
        self.host = ''
        self.status = 200
        self.body = b'{}'

    def answer(self, status: int, body: bytes) -> None:
        self.status = status
        self.body = body


def _handler_class(stub: ApiStub):
    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self._answer()

        def do_POST(self):
            self._answer()

        def do_PUT(self):
            self._answer()

        def do_DELETE(self):
            self._answer()

        def log_message(self, log_format, *args):
            """Заглушка не пишет в stderr прогона."""

        def _answer(self):
            self.send_response(stub.status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(stub.body)))
            self.end_headers()
            self.wfile.write(stub.body)

    return _Handler


@pytest.fixture(scope='module')
def api_stub():
    stub = ApiStub()
    server = ThreadingHTTPServer(('127.0.0.1', 0), _handler_class(stub))
    stub.host = 'http://127.0.0.1:{port}'.format(port=server.server_address[1])
    threading.Thread(target=server.serve_forever, daemon=True).start()

    yield stub

    server.shutdown()
    server.server_close()


@pytest.fixture
def api_config(cli_config, api_stub):
    """Конфиг CLI, указывающий на заглушку вместо боевого хоста бренда."""
    with open(cli_config) as config_file:
        config = yaml.safe_load(config_file)
    config['host'] = api_stub.host
    with open(cli_config, 'w') as config_file:
        yaml.dump(config, config_file)
    return api_stub


def _invoke(command):
    return CliRunner().invoke(entry_point, ('-k', APIKEY) + tuple(command))


def _assert_reported_without_traceback(result) -> None:
    assert result.exit_code != 0
    assert 'Traceback' not in result.output
    # Наружу уходит только выход click'а: необработанное исключение печатает traceback.
    assert result.exc_info[0] is SystemExit


@pytest.mark.parametrize('command', COMMANDS, ids=COMMAND_IDS)
def test_forbidden_is_reported_with_the_reason_of_the_api(api_config, command):
    api_config.answer(
        FORBIDDEN, json.dumps({'errors': ['Service is not available']}).encode(),
    )

    result = _invoke(command)

    assert 'Service is not available' in result.output
    _assert_reported_without_traceback(result)


@pytest.mark.parametrize('command', COMMANDS, ids=COMMAND_IDS)
def test_not_found_is_reported_as_missing_object(api_config, command):
    api_config.answer(NOT_FOUND, b'{"errors": ["no such object"]}')

    result = _invoke(command)

    assert 'object not found' in result.output
    _assert_reported_without_traceback(result)


@pytest.mark.parametrize('body', (
    b'{"message": "no access to the project"}',
    b'"no access to the project"',
    b'no access to the project',
))
def test_forbidden_outside_the_contract_form_is_still_readable(api_config, body):
    """403 отдаёт не только сам API: тело без `errors` и не в JSON тоже должно читаться."""
    api_config.answer(FORBIDDEN, body)

    result = _invoke(COMMANDS[0])

    assert 'no access to the project' in result.output
    _assert_reported_without_traceback(result)
