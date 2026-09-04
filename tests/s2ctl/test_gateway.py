import pytest
from click.testing import CliRunner

from s2ctl.entrypoint import entry_point
from ssclient.gateway.gateway_id import GATEWAY_ID_TEMPLATE
from ssclient.network.network_id import NETWORK_ID_TEMPLATE
from tests.conftest import FakeRequest
from tests.ssclient.gateway.conftest import GATEWAY_PATH, GATEWAYS_PATH, RAW_GATEWAY_ID

_USAGE_ERROR_EXIT_CODE = 2

NIC_ID = 3
NICS_PATH = '{gateway_path}/nics'.format(gateway_path=GATEWAY_PATH)
NIC_PATH = '{nics_path}/{nic_id}'.format(nics_path=NICS_PATH, nic_id=NIC_ID)
FIREWALL_PATH = '{gateway_path}/firewall'.format(gateway_path=GATEWAY_PATH)
NAT_PATH = '{gateway_path}/nat'.format(gateway_path=GATEWAY_PATH)

GATEWAY_ENTITY = {'id': RAW_GATEWAY_ID, 'location_id': 'l1', 'name': 'gw'}

FIREWALL_RULE = {
    'action': 'Allow',
    'direction': 'In',
    'protocol': 'TCP',
    'source': '0.0.0.0/0',
    'source_port': 0,
    'destination': '10.0.0.1',
    'destination_port': 443,
}

NAT_RULE = {
    'type': 'DNAT',
    'protocol': 'TCP',
    'source': '0.0.0.0/0',
    'destination': '203.0.113.1',
    'destination_port': 443,
    'translated': '10.0.0.1',
    'translated_port': 443,
}

# Наборы правил publisher принимает только под своим ключом-обёрткой и требует его
# непустым (`[EncodedRequired]`): голый массив в теле — 400 на любом вызове.
_RULE_SET_CASES = (
    ('replace-firewall', FIREWALL_PATH, 'firewall_rules', FIREWALL_RULE),
    ('replace-nat', NAT_PATH, 'nat_rules', NAT_RULE),
)

# Имена опций и имена полей контракта расходятся: `--location` кладётся в `location_id`,
# `--bandwidth` — в `bandwidth_mbps`, повторяемый `--network-id` — в массив `network_ids`.
_CONTRACT_FIELD_CASES = (
    (
        (
            'create',
            '--location', 'am2', '--name', 'gw', '--bandwidth', '100',
            '--network-id', 'l1n2', '--network-id', 'l1n3',
        ),
        FakeRequest('POST', GATEWAYS_PATH, {
            'location_id': 'am2',
            'name': 'gw',
            'bandwidth_mbps': 100,
            'network_ids': ['l1n2', 'l1n3'],
        }),
        {'task_id': 'l1t9'},
    ),
    (
        ('set-bandwidth', RAW_GATEWAY_ID, '--bandwidth', '100'),
        FakeRequest('PUT', '{gateway_path}/bandwidth'.format(gateway_path=GATEWAY_PATH), {
            'bandwidth_mbps': 100,
        }),
        {'task_id': 'l1t9'},
    ),
    (
        ('rename', RAW_GATEWAY_ID, '--name', 'gw-renamed'),
        FakeRequest('PUT', GATEWAY_PATH, {'name': 'gw-renamed'}),
        {'gateway': GATEWAY_ENTITY},
    ),
    (
        ('add-nic', RAW_GATEWAY_ID, '--network-id', 'l1n2'),
        FakeRequest('POST', NICS_PATH, {'network_id': 'l1n2'}),
        {'task_id': 'l1t9'},
    ),
)

# Питание шлюза — три команды на три маршрута: маршрут выбирается именем команды,
# а не полем в теле, и перепутать соседей нельзя.
_POWER_COMMANDS = (
    ('start', '{gateway_path}/start'.format(gateway_path=GATEWAY_PATH)),
    ('stop', '{gateway_path}/stop'.format(gateway_path=GATEWAY_PATH)),
    ('restart', '{gateway_path}/restart'.format(gateway_path=GATEWAY_PATH)),
)

# Пустой набор правил — валидный ответ API, и машинный формат обязан напечатать
# документ, который скрипту есть чем разобрать.
_EMPTY_SET_DOCUMENTS = (
    ('json', '[]'),
    ('yaml', '{}'),
)

# Ссылку на задачу удаления publisher отдаёт только по `return_task=true`; без него
# ответ пуст и `--wait` нечего ждать.
_DELETE_COMMANDS = (
    (('delete', RAW_GATEWAY_ID), GATEWAY_PATH),
    (('delete-nic', RAW_GATEWAY_ID, '--nic-id', str(NIC_ID)), NIC_PATH),
)


def _invoke(*args):
    return CliRunner().invoke(entry_point, ('-k', '02dadsd', 'gateway') + args)


# cli_config — autouse, объявлена явно: без неё прогон пишет конфиг и keyring в домашний каталог.
def test_malformed_gateway_id_is_reported_as_bad_parameter(cli_config):
    result = _invoke('get', 'e1l2')

    assert result.exit_code == _USAGE_ERROR_EXIT_CODE
    # Разбор id падает до запроса: пользователь видит формат id, а не traceback.
    assert GATEWAY_ID_TEMPLATE in result.output
    assert result.exc_info[0] is SystemExit


def test_malformed_network_id_of_new_nic_is_reported_as_bad_parameter(cli_config):
    result = _invoke('add-nic', 'l1e2', '--network-id', 'n1l3')

    assert result.exit_code == _USAGE_ERROR_EXIT_CODE
    assert NETWORK_ID_TEMPLATE in result.output
    assert result.exc_info[0] is SystemExit


@pytest.mark.parametrize('command_args,expected_request,response', _CONTRACT_FIELD_CASES)
def test_command_options_reach_the_fields_of_the_contract(
    cli_http_client, command_args, expected_request, response,
):
    cli_http_client.on(expected_request.method, expected_request.path, response)

    result = _invoke(*command_args)

    assert result.exit_code == 0, result.output
    assert cli_http_client.requests == [expected_request]


@pytest.mark.parametrize('command_name,path,rules_key,rule', _RULE_SET_CASES)
def test_replaced_rule_set_travels_under_the_key_of_the_contract(
    cli_http_client, rules_file, command_name, path, rules_key, rule,
):
    cli_http_client.on('PUT', path, {'task_id': 'l1t9'})

    result = _invoke(command_name, RAW_GATEWAY_ID, '--rules-file', rules_file([rule]))

    assert result.exit_code == 0, result.output
    assert cli_http_client.requests == [FakeRequest('PUT', path, {rules_key: [rule]})]


@pytest.mark.parametrize('command_name,expected_path', _POWER_COMMANDS)
def test_each_power_command_hits_its_own_route(cli_http_client, command_name, expected_path):
    cli_http_client.on('POST', expected_path, {'task_id': 'l1t9'})

    result = _invoke(command_name, RAW_GATEWAY_ID)

    assert result.exit_code == 0, result.output
    assert cli_http_client.requests == [FakeRequest('POST', expected_path, {})]


@pytest.mark.parametrize('command_args,path', _DELETE_COMMANDS)
def test_delete_asks_the_publisher_for_the_reference_to_the_task(
    cli_http_client, command_args, path,
):
    expected_path = '{path}?return_task=true'.format(path=path)
    cli_http_client.on('DELETE', expected_path, {'task_id': 'l1t9'})

    result = _invoke(*command_args)

    assert result.exit_code == 0, result.output
    assert cli_http_client.paths('DELETE') == [expected_path]


@pytest.mark.parametrize('output_format,expected_document', _EMPTY_SET_DOCUMENTS)
def test_empty_rule_set_is_printed_as_a_document_of_the_machine_format(
    cli_http_client, output_format, expected_document,
):
    cli_http_client.on('GET', FIREWALL_PATH, {'firewall_rules': []})

    result = _invoke('get-firewall', RAW_GATEWAY_ID, '--output', output_format)

    assert result.exit_code == 0, result.output
    assert result.output.strip() == expected_document


def test_empty_rule_set_prints_nothing_in_the_table_format(cli_http_client):
    cli_http_client.on('GET', FIREWALL_PATH, {'firewall_rules': []})

    result = _invoke('get-firewall', RAW_GATEWAY_ID, '--output', 'table')

    assert result.exit_code == 0, result.output
    # Пустая таблица — это пустой вывод tabulate: заголовков у набора без правил нет.
    assert result.output == ''
