"""Связка «опция CLI → поле запроса контракта» для vStack-серверов."""
import pytest
from click.testing import CliRunner

from s2ctl.entrypoint import entry_point
from ssclient.server.server_id import SERVER_ID_TEMPLATE
from tests.conftest import FakeRequest
from tests.s2ctl.conftest import APIKEY

SERVER_ID = 'l1s2'

_USAGE_ERROR_EXIT_CODE = 2

SERVERS_PATH = 'api/v1/servers'
SERVER_PATH = '{path}/{server_id}'.format(path=SERVERS_PATH, server_id=SERVER_ID)
PRICE_PATH = '{path}/price'.format(path=SERVERS_PATH)

NIC_ID = 3
NIC_PATH = '{server_path}/nics/{nic_id}'.format(server_path=SERVER_PATH, nic_id=NIC_ID)

VOLUME_ID = 20210
VOLUME_PATH = '{server_path}/volumes/{volume_id}'.format(
    server_path=SERVER_PATH, volume_id=VOLUME_ID,
)

SNAPSHOT_ID = 31
SNAPSHOT_PATH = '{server_path}/snapshots/{snapshot_id}'.format(
    server_path=SERVER_PATH, snapshot_id=SNAPSHOT_ID,
)

_PRICE_ARGS = (
    'price',
    '--location', 'am2',
    '--image', 'img',
    '--cpu', '2',
    '--ram', '4G',
    '--volume', '10G',
    '--volume', '20480',
)

# Имена опций и имена полей контракта расходятся: `--ram` кладётся в `ram_mb` и по дороге
# разворачивает суффикс размера, `--volume` — в элемент `volumes[]`, `--public-network` —
# в элемент `networks[]`, `--bandwidth` интерфейса — в `bandwidth_mbps`.
_CONTRACT_FIELD_CASES = (
    (
        ('set-configuration', SERVER_ID, '--cpu', '4', '--ram', '8G'),
        FakeRequest('PUT', SERVER_PATH, {'cpu': 4, 'ram_mb': 8192}),
    ),
    (
        ('rename', SERVER_ID, '--name', 'web'),
        FakeRequest('PUT', '{server_path}/name'.format(server_path=SERVER_PATH), {'name': 'web'}),
    ),
    (
        ('edit-nic', SERVER_ID, '--nic-id', str(NIC_ID), '--bandwidth', '100'),
        FakeRequest('PUT', NIC_PATH, {'bandwidth_mbps': 100}),
    ),
    (
        _PRICE_ARGS + ('--public-network', '100', '--public-network', '200'),
        FakeRequest('POST', PRICE_PATH, {
            'location_id': 'am2',
            'image_id': 'img',
            'cpu': 2,
            'ram_mb': 4096,
            'volumes': [{'size_mb': 10240}, {'size_mb': 20480}],
            'networks': [{'bandwidth_mbps': 100}, {'bandwidth_mbps': 200}],
        }),
    ),
)

# Задать конфигурацию целиком и изменить отдельные её поля — две операции контракта
# на двух методах одного маршрута: команда обязана бить ровно в свой.
_CONFIGURATION_COMMANDS = (
    (('set-configuration', SERVER_ID, '--cpu', '4', '--ram', '8G'), 'PUT', 'PATCH'),
    (('edit', SERVER_ID, '--cpu', '4'), 'PATCH', 'PUT'),
)


def _invoke(*args):
    return CliRunner().invoke(entry_point, ('-k', APIKEY, 'server') + args)


@pytest.mark.parametrize('command_args,expected_request', _CONTRACT_FIELD_CASES)
def test_command_options_reach_the_fields_of_the_contract(
    cli_http_client, command_args, expected_request,
):
    cli_http_client.on(expected_request.method, expected_request.path, {'task_id': 'l1t9'})

    result = _invoke(*command_args)

    assert result.exit_code == 0, result.output
    assert cli_http_client.requests == [expected_request]


@pytest.mark.parametrize('command_args,expected_method,foreign_method', _CONFIGURATION_COMMANDS)
def test_configuration_command_uses_only_its_own_method_of_the_contract(
    cli_http_client, command_args, expected_method, foreign_method,
):
    cli_http_client.on(expected_method, SERVER_PATH, {'task_id': 'l1t9'})

    result = _invoke(*command_args)

    assert result.exit_code == 0, result.output
    assert [request.method for request in cli_http_client.requests] == [expected_method]
    assert cli_http_client.paths(foreign_method) == []


def test_price_without_public_networks_sends_null_instead_of_empty_list(cli_http_client):
    cli_http_client.on('POST', PRICE_PATH, {'price': 100})

    result = _invoke(*_PRICE_ARGS)

    assert result.exit_code == 0, result.output
    # Для publisher'а `null` и `[]` разные: на `null` он считает один публичный интерфейс
    # минимальной ширины локации, на пустой список — конфигурацию вовсе без сети.
    assert cli_http_client.requests[0].payload['networks'] is None


def test_edit_volume_sends_both_fields_of_the_contract(cli_http_client):
    cli_http_client.on('PUT', VOLUME_PATH, {'task_id': 'l1t9'})

    result = _invoke(
        'edit-volume', SERVER_ID,
        '--volume-id', str(VOLUME_ID),
        '--volume-size', '20G',
        '--volume-name', 'data',
    )

    assert result.exit_code == 0, result.output
    assert cli_http_client.requests == [FakeRequest('PUT', VOLUME_PATH, {
        'name': 'data',
        'size_mb': 20480,
    })]


def test_edit_volume_refuses_to_run_without_the_new_size(cli_config):
    result = _invoke('edit-volume', SERVER_ID, '--volume-id', str(VOLUME_ID))

    # Размер — не-nullable поле операции: без него publisher отвечает 400
    # `VolumeBadSize`, поэтому команда отказывает до запроса.
    assert result.exit_code == _USAGE_ERROR_EXIT_CODE
    assert '--volume-size' in result.output


_VOLUME_COMMANDS_BY_ID = (
    ('get-volume', SERVER_ID, '--volume-id', 'boot'),
    ('delete-volume', SERVER_ID, '--volume-id', 'boot'),
    ('edit-volume', SERVER_ID, '--volume-id', 'boot', '--volume-size', '20G'),
)


@pytest.mark.parametrize('command_args', _VOLUME_COMMANDS_BY_ID)
def test_volume_id_of_the_contract_is_a_number(cli_http_client, command_args):
    result = _invoke(*command_args)

    # Id тома у publisher'а числовой: нечисловое значение отсекается до запроса,
    # как и у соседних `--nic-id` и `--snapshot-id`.
    assert result.exit_code == _USAGE_ERROR_EXIT_CODE
    assert '--volume-id' in result.output
    assert cli_http_client.requests == []


# Каждое удаление раздела спрашивает у publisher'а ссылку на задачу: без
# `return_task=true` ответ пуст, id задачи скрипту недоступен и `--wait` нечего ждать.
_DELETE_COMMANDS = (
    (('delete', SERVER_ID), SERVER_PATH),
    (('delete-volume', SERVER_ID, '--volume-id', str(VOLUME_ID)), VOLUME_PATH),
    (('delete-nic', SERVER_ID, '--nic-id', str(NIC_ID)), NIC_PATH),
    (
        ('delete-snapshot', SERVER_ID, '--snapshot-id', str(SNAPSHOT_ID)),
        SNAPSHOT_PATH,
    ),
)


@pytest.mark.parametrize('command_args,path', _DELETE_COMMANDS)
def test_delete_asks_the_publisher_for_the_reference_to_the_task(
    cli_http_client, command_args, path,
):
    expected_path = '{path}?return_task=true'.format(path=path)
    cli_http_client.on('DELETE', expected_path, {'task_id': 'l1t9'})

    result = _invoke(*command_args)

    assert result.exit_code == 0, result.output
    assert cli_http_client.paths('DELETE') == [expected_path]
    assert 'l1t9' in result.output


# Пять переходов питания — пять команд и пять маршрутов.
_POWER_COMMANDS = (
    ('power-on', 'on'),
    ('power-off', 'off'),
    ('shutdown', 'shutdown'),
    ('reboot', 'reboot'),
    ('reset', 'reset'),
)


@pytest.mark.parametrize('command_name,fragment', _POWER_COMMANDS)
def test_power_command_hits_its_own_route(cli_http_client, command_name, fragment):
    expected_path = '{server_path}/power/{fragment}'.format(
        server_path=SERVER_PATH, fragment=fragment,
    )
    cli_http_client.on('POST', expected_path, {'task_id': 'l1t9'})

    result = _invoke(command_name, SERVER_ID)

    assert result.exit_code == 0, result.output
    assert cli_http_client.requests == [FakeRequest('POST', expected_path, {})]


@pytest.mark.parametrize('command_name', ('power-off', 'reboot'))
def test_power_commands_have_no_hard_flag(cli_config, command_name):
    result = _invoke(command_name, SERVER_ID, '--hard')

    # Обесточить и погасить операционную систему — разные команды, а не одна с признаком
    # жёсткости: маршрут выбирается именем команды.
    assert result.exit_code == _USAGE_ERROR_EXIT_CODE
    assert '--hard' in result.output


def test_malformed_server_id_is_reported_as_bad_parameter(cli_config):
    result = _invoke('get', 's1l2')

    assert result.exit_code == _USAGE_ERROR_EXIT_CODE
    # Разбор id падает до запроса: пользователь видит формат id, а не отказ API.
    assert SERVER_ID_TEMPLATE in result.output
    assert result.exc_info[0] is SystemExit
