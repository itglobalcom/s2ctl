"""Связка «опция CLI → поле запроса контракта» для vStack-серверов."""
import pytest
from click.testing import CliRunner

from s2ctl.entrypoint import entry_point
from tests.conftest import FakeRequest

SERVER_ID = 'l1s2'

SERVERS_PATH = 'api/v1/servers'
SERVER_PATH = '{path}/{server_id}'.format(path=SERVERS_PATH, server_id=SERVER_ID)
PRICE_PATH = '{path}/price'.format(path=SERVERS_PATH)

NIC_ID = 3
NIC_PATH = '{server_path}/nics/{nic_id}'.format(server_path=SERVER_PATH, nic_id=NIC_ID)

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
    return CliRunner().invoke(entry_point, ('-k', '02dadsd', 'server') + args)


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
