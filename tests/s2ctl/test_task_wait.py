"""Пара опций ожидания задачи: `--wait` и `--timeout`.

Опции объявлены одним декоратором `wait_option`, поэтому проверяются на одной команде:
доезжает ли значение до ожидания в клиентском слое и что видит пользователь, когда
задача в отведённое время не уложилась. Само ожидание и его дефолт — на клиентском
слое (`tests/ssclient/test_task.py`).
"""
from click.testing import CliRunner

from s2ctl.entrypoint import entry_point
from ssclient.task_entities import TaskState
from tests.conftest import task_response
from tests.s2ctl.conftest import APIKEY
from tests.ssclient.vmware.coordinates import SERVER_ID

_USAGE_ERROR_EXIT_CODE = 2

RAW_TASK_ID = 'vmw7'
POWER_OFF_PATH = 'api/v1/vmware/servers/{server_id}/power/off'.format(server_id=SERVER_ID)
TASK_PATH = 'api/v1/tasks/{raw_id}'.format(raw_id=RAW_TASK_ID)

# Ожидание в тесте ограничено секундой: проверяется путь значения и текст отказа,
# а не длительность — реальная задача заказа сервера идёт минуты.
TIMEOUT_SECS = 1


def _invoke(*args):
    return CliRunner().invoke(
        entry_point,
        ('-k', APIKEY, 'vmware', 'server', 'power-off', str(SERVER_ID)) + args,
    )


def _hanging_task(cli_http_client):
    """Задача, которая в отведённое время не завершается: последний ответ повторяется."""
    cli_http_client.on('POST', POWER_OFF_PATH, {'task_id': RAW_TASK_ID})
    cli_http_client.on('GET', TASK_PATH, task_response(RAW_TASK_ID, TaskState.in_progress))
    return cli_http_client


def test_timeout_option_limits_the_wait_of_the_client_layer(cli_http_client):
    http_client = _hanging_task(cli_http_client)

    result = _invoke('--wait', '--timeout', str(TIMEOUT_SECS))

    # Секунда в отказе — та самая, что пришла опцией: значение доехало до ожидания задачи.
    assert 'after {timeout}s of waiting'.format(timeout=TIMEOUT_SECS) in result.output
    assert http_client.paths('GET') == [TASK_PATH]
    assert result.exit_code != 0


def test_wait_timeout_reports_that_the_task_goes_on(cli_http_client):
    _hanging_task(cli_http_client)

    result = _invoke('--wait', '--timeout', str(TIMEOUT_SECS))

    # После таймаута пользователю нужно знать, что заказ не отменён и чем его дождаться:
    # иначе он заказывает ресурс повторно на успешной операции.
    assert RAW_TASK_ID in result.output
    assert 'not canceled' in result.output
    assert 'task get {raw_id}'.format(raw_id=RAW_TASK_ID) in result.output
    assert 'Traceback' not in result.output


def test_timeout_without_wait_is_reported_as_usage_error(cli_http_client):
    result = _invoke('--timeout', str(TIMEOUT_SECS))

    # Без `--wait` команда не ждёт ничего, и таймауту нечего ограничивать: молча
    # проигнорированная опция выглядела бы как заданное ожидание.
    assert result.exit_code == _USAGE_ERROR_EXIT_CODE
    assert '--timeout' in result.output
    assert cli_http_client.requests == []


LLM_RAW_TASK_ID = 'llm12'
LLM_LOCK_PATH = 'api/v1/llm/groups/5/access-keys/17/lock'
LLM_TASK_PATH = 'api/v1/tasks/{raw_id}'.format(raw_id=LLM_RAW_TASK_ID)


def test_wait_of_llm_command_polls_the_llm_task_and_names_it_on_timeout(cli_http_client):
    cli_http_client.on('POST', LLM_LOCK_PATH, {'task_id': LLM_RAW_TASK_ID})
    cli_http_client.on('GET', LLM_TASK_PATH, task_response(LLM_RAW_TASK_ID, TaskState.in_progress))

    result = CliRunner().invoke(
        entry_point,
        ('-k', APIKEY, 'llm', 'key', 'lock', '5', '17', '--wait', '--timeout', str(TIMEOUT_SECS)),
    )

    # Задача LLM опрашивается по своему маршруту, а не отвергается разбором id.
    assert cli_http_client.paths('GET') == [LLM_TASK_PATH]
    assert 'task get {raw_id}'.format(raw_id=LLM_RAW_TASK_ID) in result.output
    assert result.exit_code != 0
