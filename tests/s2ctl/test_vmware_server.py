import pytest
from click.testing import CliRunner

from s2ctl.click import FORMATTER_NAMES
from s2ctl.entrypoint import entry_point
from tests.conftest import FakeRequest
from tests.s2ctl.conftest import APIKEY
from tests.ssclient.vmware.conftest import (
    NIC_ID,
    NIC_PATH,
    NICS_PATH,
    SERVER_ID,
    SERVER_PATH,
    SERVERS_PATH,
    SHARED_NICS_PATH,
    SNAPSHOT_PATH,
    VOLUME_ID,
    VOLUME_PATH,
    VOLUMES_PATH,
)

FIREWALL_PATH = '{server_path}/firewall'.format(server_path=SERVER_PATH)
VERIFY_PATH = '{path}/verify'.format(path=SERVERS_PATH)

FIREWALL_RULE = {
    'name': 'ssh',
    'traffic_direction': 'Incoming',
    'action': 'Allow',
    'protocol': 'Tcp',
    'source': '0.0.0.0/0',
    'source_port': 'any',
    'destination': '10.0.0.1',
    'destination_port': '22',
}

_USAGE_ERROR_EXIT_CODE = 2

POWER_PATH = '{server_path}/power'.format(server_path=SERVER_PATH)

# Каждый переход питания — своя команда: пять команд бьют в пять маршрутов.
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

# Заказ сервера — 16 опций, и ни одна не названа именем своего поля контракта.
_FULL_ORDER_ARGS = _CREATE_ARGS + (
    '--computer-name', 'web-01',
    '--system-disk-type', 'ssd',
    '--public-network', '42',
    '--bandwidth', '100',
    '--backup',
    '--backup-period', '7',
    '--ssh-key', '3',
    '--ssh-key', '4',
    '--sysprep',
    '--nested-hypervisor',
    '--gpu', '3:8192:1',
)

_FULL_ORDER_PAYLOAD = {
    'location_id': 1,
    'name': 'srv',
    'image_id': 5,
    'cpu_count': 2,
    'ram_mb': 4096,
    'system_disk_size_mb': 51200,
    'computer_name': 'web-01',
    'system_disk_type': 'ssd',
    'public_network_id': 42,
    'network_bandwidth_mbps': 100,
    'backup_enabled': True,
    'backup_period': 7,
    'ssh_keys': [3, 4],
    'need_sysprep': True,
    'nested_hypervisor': True,
    'gpu': {'gpu_model_id': 3, 'vram_mb': 8192, 'card_count': 1},
}

# Заказ и его предпроверка — одно тело на два маршрута: разойдясь, они перестанут
# проверять одно и то же, и предпроверка начнёт врать о заказе.
_ORDER_ROUTES = (
    ('create', SERVERS_PATH),
    ('verify', VERIFY_PATH),
)


def _invoke(*args):
    return CliRunner().invoke(entry_point, ('-k', APIKEY, 'vmware', 'server') + args)


@pytest.mark.parametrize('command_name,expected_path', POWER_COMMANDS)
def test_each_power_command_hits_its_own_route(cli_http_client, command_name, expected_path):
    cli_http_client.on('POST', expected_path, {'task_id': 'vmw55'})

    result = _invoke(command_name, str(SERVER_ID))

    assert result.exit_code == 0, result.output
    assert cli_http_client.paths('POST') == [expected_path]


@pytest.mark.parametrize('command_name', ('power-off', 'reboot'))
def test_power_commands_have_no_hard_flag(cli_config, command_name):
    result = CliRunner().invoke(
        entry_point, ('-k', APIKEY, 'vmware', 'server', command_name, str(SERVER_ID), '--hard'),
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
        '-k', APIKEY, 'vmware', 'server', 'create',
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
    (
        ('set-configuration', '--cpu', '4', '--ram', '8192', '--system-disk-size', '51200'),
        # Конфигурация задаётся целиком: частичной правки у этого маршрута нет,
        # и все три поля уходят в запрос всегда.
        FakeRequest('PUT', SERVER_PATH, {
            'cpu': 4,
            'ram_mb': 8192,
            'system_disk_size_mb': 51200,
        }),
    ),
    (
        ('set-computer-name', '--computer-name', 'web-01', '--force-customization'),
        FakeRequest('PUT', '{server_path}/computer-name'.format(server_path=SERVER_PATH), {
            'computer_name': 'web-01',
            'force_customization': True,
        }),
    ),
    (
        ('copy', '--name', 'srv-copy', '--client-network', '42'),
        FakeRequest('POST', '{server_path}/copy'.format(server_path=SERVER_PATH), {
            'name': 'srv-copy',
            'client_network_id': 42,
        }),
    ),
    (
        ('rebuild', '--image', '5', '--sysprep'),
        FakeRequest('POST', '{server_path}/rebuild'.format(server_path=SERVER_PATH), {
            'image_id': 5,
            'need_sysprep': True,
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
        '-k', APIKEY, 'vmware', 'server', command_name, str(SERVER_ID),
    ) + required_args + ('--snapshot-id', '5'))

    assert result.exit_code == _USAGE_ERROR_EXIT_CODE
    assert '--snapshot-id' in result.output


@pytest.mark.parametrize('output_format', FORMATTER_NAMES)
def test_get_snapshot_of_a_server_without_snapshot_prints_nothing(
    cli_http_client, output_format,
):
    # Тело без снимка — фактическая форма ответа живого API: ключа `snapshot` в нём
    # нет вовсе, null-поля publisher из ответа выбрасывает. Печатать нечего, но это
    # штатный исход команды, а не отказ.
    cli_http_client.on('GET', SNAPSHOT_PATH, {})

    result = _invoke('get-snapshot', str(SERVER_ID), '-o', output_format)

    assert result.exit_code == 0, result.output
    assert not result.output


def test_connect_client_network_has_no_shared_flag(cli_config):
    result = CliRunner().invoke(entry_point, (
        '-k', APIKEY, 'vmware', 'server', 'connect-client-network', str(SERVER_ID),
        '--network', '42', '--shared',
    ))

    # Общая сеть подключается своей командой по своему маршруту: признака общей сети
    # у команды клиентской сети нет и быть не должно.
    assert result.exit_code == _USAGE_ERROR_EXIT_CODE
    assert '--shared' in result.output


@pytest.mark.parametrize('command_name,expected_path', _ORDER_ROUTES)
def test_order_options_reach_every_field_of_the_contract(
    cli_http_client, command_name, expected_path,
):
    cli_http_client.on('POST', expected_path, {'server_id': 777, 'task_id': 'vmw11'})

    result = _invoke(command_name, *_FULL_ORDER_ARGS)

    assert result.exit_code == 0, result.output
    assert cli_http_client.requests == [
        FakeRequest('POST', expected_path, _FULL_ORDER_PAYLOAD),
    ]


def test_replace_firewall_wraps_the_rule_set_in_the_key_of_the_contract(
    cli_http_client, rules_file,
):
    cli_http_client.on('PUT', FIREWALL_PATH, {'task_id': 'vmw12'})

    result = _invoke('replace-firewall', str(SERVER_ID), '--rules-file', rules_file([FIREWALL_RULE]))

    assert result.exit_code == 0, result.output
    # Набор правил уезжает под ключом-обёрткой контракта, а не голым массивом.
    assert cli_http_client.requests == [
        FakeRequest('PUT', FIREWALL_PATH, {'rules': [FIREWALL_RULE]}),
    ]
