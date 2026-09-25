"""Связка «опция CLI → запрос контракта» для раздела бэкапа vStack-сервера."""
import json

import pytest
from click.testing import CliRunner

from s2ctl.entrypoint import entry_point
from ssclient.task_entities import TaskState
from tests.conftest import FakeRequest, task_response
from tests.s2ctl.conftest import APIKEY

SERVER_ID = 'l1s2'
BACKUP_PATH = 'api/v1/servers/{server_id}/backup'.format(server_id=SERVER_ID)
POINTS_PATH = '{path}/restore-points'.format(path=BACKUP_PATH)
POINT_ID = 41
POINT_PATH = '{path}/{point_id}'.format(path=POINTS_PATH, point_id=POINT_ID)
TASK_ID = 'l1t9'
TASK_PATH = 'api/v1/tasks/{task_id}'.format(task_id=TASK_ID)
TASK_WRAP = {'task_id': TASK_ID}

_USAGE_ERROR_EXIT_CODE = 2

SCHEDULE = {
    'hour': 3,
    'minute': 30,
    'daily': {'keep': 7, 'backup_storage_id': 5},
    'weekly': {'keep': 4, 'backup_storage_id': 5, 'weekday': 'monday'},
}


def _invoke(*args):
    return CliRunner().invoke(entry_point, ('-k', APIKEY, 'server') + args)


def _point(point_id: int, state: str):
    return {
        'id': point_id,
        'server_id': SERVER_ID,
        'size_mb': 1024,
        'state': state,
        'retained_by': [],
        'is_manual': True,
    }


@pytest.fixture
def schedule_file(tmp_path):
    def factory(content) -> str:
        path = tmp_path / 'schedule.json'
        path.write_text(json.dumps(content))
        return str(path)

    return factory


# Мутации раздела без `--wait` печатают ссылку на задачу; тело запроса — поля контракта.
_TASK_COMMAND_CASES = (
    (('disable-backup', SERVER_ID), FakeRequest('DELETE', BACKUP_PATH)),
    (('create-restore-point', SERVER_ID), FakeRequest('POST', POINTS_PATH, {})),
    (
        ('create-restore-point', SERVER_ID, '--name', 'before-upgrade'),
        FakeRequest('POST', POINTS_PATH, {'name': 'before-upgrade'}),
    ),
    (
        ('restore-backup', SERVER_ID, '--restore-point-id', str(POINT_ID)),
        FakeRequest('POST', '{path}/restore'.format(path=POINT_PATH), {}),
    ),
    (
        ('restore-backup-nearby', SERVER_ID, '--restore-point-id', str(POINT_ID)),
        FakeRequest('POST', '{path}/restore-nearby'.format(path=POINT_PATH), {}),
    ),
    (
        ('restore-backup-nearby', SERVER_ID, '--restore-point-id', str(POINT_ID), '--location', 'am2'),
        FakeRequest('POST', '{path}/restore-nearby'.format(path=POINT_PATH), {'location_id': 'am2'}),
    ),
    (
        ('delete-restore-point', SERVER_ID, '--restore-point-id', str(POINT_ID)),
        FakeRequest('DELETE', '{path}?return_task=true'.format(path=POINT_PATH)),
    ),
)


@pytest.mark.parametrize('command_args,expected_request', _TASK_COMMAND_CASES)
def test_mutation_sends_its_request_and_prints_the_task(
    cli_http_client, command_args, expected_request,
):
    cli_http_client.on(expected_request.method, expected_request.path, TASK_WRAP)

    result = _invoke(*command_args + ('--output', 'json'))

    assert result.exit_code == 0, result.output
    assert cli_http_client.requests == [expected_request]
    assert json.loads(result.output) == TASK_WRAP


# Расписание из файла уходит телом операции как есть; файл вывода `get-backup`
# принимается целиком — расписание берётся из его `schedule`.
_SCHEDULE_COMMANDS = (
    ('enable-backup', 'POST'),
    ('set-backup-schedule', 'PUT'),
)


@pytest.mark.parametrize('command_name,method', _SCHEDULE_COMMANDS)
@pytest.mark.parametrize('file_content', (SCHEDULE, {'enabled': True, 'schedule': SCHEDULE}))
def test_schedule_command_sends_the_schedule_of_the_file(
    cli_http_client, schedule_file, command_name, method, file_content,
):
    cli_http_client.on(method, BACKUP_PATH, TASK_WRAP)

    result = _invoke(command_name, SERVER_ID, '--schedule-file', schedule_file(file_content))

    assert result.exit_code == 0, result.output
    assert cli_http_client.requests == [FakeRequest(method, BACKUP_PATH, SCHEDULE)]


@pytest.mark.parametrize('command_name,method', _SCHEDULE_COMMANDS)
def test_schedule_command_with_wait_prints_the_backup(
    cli_http_client, schedule_file, command_name, method,
):
    backup = {'enabled': True, 'schedule': SCHEDULE}
    cli_http_client.on(method, BACKUP_PATH, TASK_WRAP)
    cli_http_client.on('GET', TASK_PATH, task_response(TASK_ID, TaskState.completed))
    cli_http_client.on('GET', BACKUP_PATH, backup)

    result = _invoke(
        command_name, SERVER_ID, '--schedule-file', schedule_file(SCHEDULE), '--wait', '--output', 'json',
    )

    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == backup


# Вывод `get-backup` сервера без услуги расписания не несёт: отправлять нечего.
@pytest.mark.parametrize('file_content', ({'enabled': False}, [SCHEDULE]))
def test_schedule_file_without_a_schedule_is_a_usage_error(
    cli_http_client, schedule_file, file_content,
):
    result = _invoke('enable-backup', SERVER_ID, '--schedule-file', schedule_file(file_content))

    assert result.exit_code == _USAGE_ERROR_EXIT_CODE
    assert '--schedule-file' in result.output
    assert cli_http_client.requests == []


@pytest.mark.parametrize('weekday', (1, 'mon', 'Monday'))
def test_schedule_file_with_unknown_weekday_is_a_usage_error(
    cli_http_client, schedule_file, weekday,
):
    weekly = dict(SCHEDULE['weekly'], weekday=weekday)

    result = _invoke(
        'enable-backup', SERVER_ID, '--schedule-file', schedule_file(dict(SCHEDULE, weekly=weekly)),
    )

    assert result.exit_code == _USAGE_ERROR_EXIT_CODE
    assert 'monday' in result.output
    assert cli_http_client.requests == []


def test_create_sends_the_backup_schedule_with_the_order(cli_http_client, schedule_file):
    cli_http_client.on('POST', 'api/v1/servers', {'task_id': TASK_ID, 'server_id': SERVER_ID})

    result = _invoke(
        'create',
        '--name', 'web',
        '--location', 'am2',
        '--image', 'am2i5',
        '--cpu', '2',
        '--ram', '2G',
        '--volume', '20G',
        '--public-network', '100',
        '--backup-schedule-file', schedule_file(SCHEDULE),
    )

    assert result.exit_code == 0, result.output
    assert cli_http_client.requests[0].payload['backup'] == SCHEDULE


def test_create_without_backup_schedule_orders_no_backup(cli_http_client):
    cli_http_client.on('POST', 'api/v1/servers', {'task_id': TASK_ID, 'server_id': SERVER_ID})

    result = _invoke(
        'create',
        '--name', 'web',
        '--location', 'am2',
        '--image', 'am2i5',
        '--cpu', '2',
        '--ram', '2G',
        '--volume', '20G',
        '--public-network', '100',
    )

    assert result.exit_code == 0, result.output
    assert 'backup' not in cli_http_client.requests[0].payload


def _on_manual_copy(cli_http_client, taken_point):
    cli_http_client.on(
        'GET', POINTS_PATH,
        {'restore_points': []},
        {'restore_points': [taken_point]},
    )
    cli_http_client.on('POST', POINTS_PATH, TASK_WRAP)
    cli_http_client.on('GET', TASK_PATH, task_response(TASK_ID, TaskState.completed))


def test_create_restore_point_with_wait_prints_the_taken_point(cli_http_client):
    taken_point = _point(POINT_ID, 'active')
    _on_manual_copy(cli_http_client, taken_point)

    result = _invoke('create-restore-point', SERVER_ID, '--wait', '--output', 'json')

    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == taken_point


def test_create_restore_point_with_wait_fails_when_the_copy_failed(cli_http_client):
    _on_manual_copy(cli_http_client, _point(POINT_ID, 'failed'))

    result = _invoke('create-restore-point', SERVER_ID, '--wait')

    assert result.exit_code != 0
    assert str(POINT_ID) in result.output
    assert TASK_ID in result.output


def test_create_restore_point_with_wait_fails_without_a_new_point(cli_http_client):
    cli_http_client.on('GET', POINTS_PATH, {'restore_points': []})
    cli_http_client.on('POST', POINTS_PATH, TASK_WRAP)
    cli_http_client.on('GET', TASK_PATH, task_response(TASK_ID, TaskState.completed))

    result = _invoke('create-restore-point', SERVER_ID, '--wait')

    assert result.exit_code != 0
    assert TASK_ID in result.output


_READ_COMMANDS = (
    (('get-backup', SERVER_ID), BACKUP_PATH, {'enabled': False}, {'enabled': False}),
    (
        ('list-backup-storage', SERVER_ID),
        '{path}/storages'.format(path=BACKUP_PATH),
        {'storages': [], 'limits': {}},
        {'storages': [], 'limits': {}},
    ),
    (
        ('list-restore-point', SERVER_ID),
        POINTS_PATH,
        {'restore_points': [_point(POINT_ID, 'active')]},
        [_point(POINT_ID, 'active')],
    ),
)


@pytest.mark.parametrize('command_args,path,response,printed', _READ_COMMANDS)
def test_read_command_prints_the_response_of_the_contract(
    cli_http_client, command_args, path, response, printed,
):
    cli_http_client.on('GET', path, response)

    result = _invoke(*command_args + ('--output', 'json'))

    assert result.exit_code == 0, result.output
    assert cli_http_client.paths('GET') == [path]
    assert json.loads(result.output) == printed


def test_restore_point_id_of_the_contract_is_a_number(cli_http_client):
    result = _invoke('restore-backup', SERVER_ID, '--restore-point-id', 'last')

    assert result.exit_code == _USAGE_ERROR_EXIT_CODE
    assert '--restore-point-id' in result.output
    assert cli_http_client.requests == []
