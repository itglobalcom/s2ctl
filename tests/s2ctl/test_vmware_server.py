import pytest
from click.testing import CliRunner

from s2ctl import cmd_vmware
from s2ctl.entrypoint import entry_point
from ssclient.client import SSClient
from tests.conftest import FakeRequest
from tests.ssclient.vmware.conftest import (
    NIC_ID,
    NIC_PATH,
    NICS_PATH,
    SERVER_ID,
    SERVER_PATH,
    SERVERS_PATH,
    SHARED_NICS_PATH,
    VOLUME_ID,
    VOLUME_PATH,
    VOLUMES_PATH,
)

_USAGE_ERROR_EXIT_CODE = 2

POWER_PATH = '{server_path}/power'.format(server_path=SERVER_PATH)

# Каждый переход питания — своя команда: пять команд бьют в пять маршрутов. Легаси-раздел
# vStack склеивает пары флагом `--hard`, здесь такой склейки нет и заводить её нельзя.
POWER_COMMANDS = (
    ('power-on', '{path}/on'.format(path=POWER_PATH)),
    ('power-off', '{path}/off'.format(path=POWER_PATH)),
    ('shutdown', '{path}/shutdown'.format(path=POWER_PATH)),
    ('reboot', '{path}/reboot'.format(path=POWER_PATH)),
    ('reset', '{path}/reset'.format(path=POWER_PATH)),
)

_CREATE_ARGS = (
    '--location', '1',
    '--name', 'srv',
    '--image', '5',
    '--cpu', '2',
    '--ram', '4096',
    '--system-disk-size', '51200',
)


@pytest.fixture
def cli_http_client(monkeypatch, fake_http_client):
    """Группа `vmware` строит сервис фабрикой клиента — подменяется она, а не сам сервис."""
    monkeypatch.setattr(cmd_vmware, 'client_factory', lambda _ctx: SSClient(fake_http_client))
    return fake_http_client


def _invoke(*args):
    return CliRunner().invoke(entry_point, ('-k', '02dadsd', 'vmware', 'server') + args)


@pytest.mark.parametrize('command_name,expected_path', POWER_COMMANDS)
def test_each_power_command_hits_its_own_route(cli_http_client, command_name, expected_path):
    cli_http_client.on('POST', expected_path, {'task_id': 'vmw55'})

    result = _invoke(command_name, str(SERVER_ID))

    assert result.exit_code == 0, result.output
    assert cli_http_client.paths('POST') == [expected_path]


@pytest.mark.parametrize('command_name', ('power-off', 'reboot'))
def test_power_commands_have_no_hard_flag(cli_config, command_name):
    result = CliRunner().invoke(
        entry_point, ('-k', '02dadsd', 'vmware', 'server', command_name, str(SERVER_ID), '--hard'),
    )

    # Обесточить и погасить гостевую ОС — разные команды, а не одна с признаком жёсткости.
    assert result.exit_code == _USAGE_ERROR_EXIT_CODE
    assert '--hard' in result.output


def test_gpu_triple_is_sent_as_the_whole_profile(cli_http_client):
    cli_http_client.on('POST', SERVERS_PATH, {'server_id': 777, 'task_id': 'vmw11'})

    result = _invoke('create', *_CREATE_ARGS, '--gpu', '3:8192:1')

    assert result.exit_code == 0, result.output
    order_payload = cli_http_client.requests[0].payload
    assert order_payload['gpu'] == {'gpu_model_id': 3, 'vram_mb': 8192, 'card_count': 1}


def test_malformed_gpu_is_reported_as_bad_parameter(cli_config):
    result = CliRunner().invoke(entry_point, (
        '-k', '02dadsd', 'vmware', 'server', 'create',
    ) + _CREATE_ARGS + ('--gpu', '3:8192'))

    # Разбор тройки падает до запроса: пользователь видит формат, а не общую ошибку команды.
    assert result.exit_code == _USAGE_ERROR_EXIT_CODE
    assert 'MODEL_ID:VRAM_MB:CARD_COUNT' in result.output


# Опции команд названы по-человечески, а поля контракта — по-своему: проверяется, что
# значение доезжает до поля запроса. Подключение к клиентской сети и к общей — две
# команды на два маршрута с разными телами, а не одна команда с признаком общей сети.
_CONTRACT_FIELD_CASES = (
    (
        ('add-volume', '--name', 'data', '--disk-type', 'ssd', '--size', '10240'),
        FakeRequest('POST', VOLUMES_PATH, {
            'name': 'data',
            'disk_type': 'ssd',
            'size_mb': 10240,
        }),
    ),
    (
        ('edit-volume', '--volume-id', str(VOLUME_ID), '--size', '20480'),
        FakeRequest('PUT', VOLUME_PATH, {'name': None, 'size_mb': 20480}),
    ),
    (
        ('connect-client-network', '--network', '42', '--ip', '10.0.0.5'),
        FakeRequest('POST', NICS_PATH, {
            'network_id': 42,
            'ip': '10.0.0.5',
            'force_customization': False,
        }),
    ),
    (
        ('connect-shared-network', '--bandwidth', '100'),
        FakeRequest('POST', SHARED_NICS_PATH, {
            'bandwidth_mbps': 100,
            'force_customization': False,
        }),
    ),
    (
        ('edit-nic', '--nic-id', str(NIC_ID), '--network', '42', '--bandwidth', '200'),
        FakeRequest('PUT', NIC_PATH, {
            'network_id': 42,
            'bandwidth_mbps': 200,
            'ip': None,
            'force_customization': False,
        }),
    ),
)

# Снимок у VMware-сервера один, и контракт адресует его сервером: id снимка команды
# не принимают. Защита от переноса команд из раздела vStack, где снимков много.
_SNAPSHOT_COMMANDS = (
    ('get-snapshot', ()),
    ('create-snapshot', ('--name', 'before-update')),
    ('restore-snapshot', ()),
    ('delete-snapshot', ()),
)


@pytest.mark.parametrize('command_args,expected_request', _CONTRACT_FIELD_CASES)
def test_command_options_reach_the_fields_of_the_contract(
    cli_http_client, command_args, expected_request,
):
    cli_http_client.on(expected_request.method, expected_request.path, {'task_id': 'vmw99'})

    command_name = command_args[0]
    result = _invoke(command_name, str(SERVER_ID), *command_args[1:])

    assert result.exit_code == 0, result.output
    assert cli_http_client.requests == [expected_request]


@pytest.mark.parametrize('command_name,required_args', _SNAPSHOT_COMMANDS)
def test_snapshot_commands_take_no_snapshot_id(cli_config, command_name, required_args):
    result = CliRunner().invoke(entry_point, (
        '-k', '02dadsd', 'vmware', 'server', command_name, str(SERVER_ID),
    ) + required_args + ('--snapshot-id', '5'))

    assert result.exit_code == _USAGE_ERROR_EXIT_CODE
    assert '--snapshot-id' in result.output


def test_connect_client_network_has_no_shared_flag(cli_config):
    result = CliRunner().invoke(entry_point, (
        '-k', '02dadsd', 'vmware', 'server', 'connect-client-network', str(SERVER_ID),
        '--network', '42', '--shared',
    ))

    # Общая сеть подключается своей командой по своему маршруту: признака общей сети
    # у команды клиентской сети нет и быть не должно.
    assert result.exit_code == _USAGE_ERROR_EXIT_CODE
    assert '--shared' in result.output
