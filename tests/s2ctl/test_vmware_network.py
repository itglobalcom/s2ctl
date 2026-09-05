"""Связка «опция CLI → поле запроса контракта» для сетей VMware и их edge-шлюза.

Проверяется тело запроса, а не то, что клиентский слой отправил ровно то, что отправил:
у команд, чьё тело — подмножество полей request-DTO publisher'а, отдельно ассертится
наличие полей, без которых publisher отвечает 400.
"""
import pytest
from click.testing import CliRunner

from s2ctl.entrypoint import entry_point
from tests.conftest import FakeRequest
from tests.s2ctl.conftest import APIKEY
from tests.ssclient.vmware.conftest import (
    EDIT_NETWORK_REQUIRED_FIELDS,
    EDGE_PATH,
    NETWORK_ENTITY,
    NETWORK_ID,
    NETWORK_PATH,
    NETWORKS_PATH,
)

_USAGE_ERROR_EXIT_CODE = 2

CONNECT_SERVERS_PATH = '{network_path}/servers'.format(network_path=NETWORK_PATH)

EDGE_BANDWIDTH_PATH = '{edge_path}/bandwidth'.format(edge_path=EDGE_PATH)
EDGE_FIREWALL_PATH = '{edge_path}/firewall'.format(edge_path=EDGE_PATH)
EDGE_NAT_PATH = '{edge_path}/nat'.format(edge_path=EDGE_PATH)
EDGE_VPN_PATH = '{edge_path}/vpn'.format(edge_path=EDGE_PATH)

FIREWALL_RULE = {
    'name': 'ssh',
    'action': 'Allow',
    'protocol': 'Tcp',
    'source': '0.0.0.0/0',
    'source_port': 'any',
    'destination': '10.0.0.1',
    'destination_port': '22',
}

_VPN_ARGS = (
    '--name', 'to-office',
    '--shared-key', 'secret',
    '--peer-network', '192.168.0.0/24',
    '--peer-endpoint', '198.51.100.7',
    '--peer-identificator', 'office',
    '--mtu', '1400',
    '--encryption-type', 'Aes256',
    '--diffie-hellman-group', 'DH14',
)

_VPN_PAYLOAD = {
    'name': 'to-office',
    'enabled': None,
    'mtu': 1400,
    'encryption_type': 'Aes256',
    'shared_key': 'secret',
    'peer_network': '192.168.0.0/24',
    'peer_endpoint': '198.51.100.7',
    'peer_identificator': 'office',
    'perfect_forward_secrecy': None,
    'diffie_hellman_group': 'DH14',
}

# Имена опций и имена полей контракта совпадают далеко не везде: `--location` кладётся
# в `location_id`, `--bandwidth` — в `bandwidth_mbps`, `--dhcp` — в `enable_dhcp`,
# `--capacity` — в имя члена enum, а `--server SERVER_ID[:IP]` — в элемент `nics[]`.
_NETWORK_CASES = (
    (
        (
            'create-isolated',
            '--location', '1', '--name', 'net', '--address', '10.0.0.0', '--mask', '24', '--dhcp',
        ),
        FakeRequest('POST', '{path}/isolated'.format(path=NETWORKS_PATH), {
            'location_id': 1,
            'name': 'net',
            'address': '10.0.0.0',
            'mask': 24,
            'enable_dhcp': True,
        }),
    ),
    (
        (
            'create-routed',
            '--location', '1', '--name', 'net', '--address', '10.0.0.0',
            '--mask', '24', '--bandwidth', '100',
        ),
        FakeRequest('POST', '{path}/routed'.format(path=NETWORKS_PATH), {
            'location_id': 1,
            'name': 'net',
            'address': '10.0.0.0',
            'mask': 24,
            'enable_dhcp': False,
            'bandwidth_mbps': 100,
        }),
    ),
    (
        ('create-public', '--location', '1', '--name', 'net', '--capacity', 'Network26'),
        FakeRequest('POST', '{path}/public'.format(path=NETWORKS_PATH), {
            'location_id': 1,
            'name': 'net',
            'capacity': 'Network26',
            'bandwidth_mbps': None,
        }),
    ),
    (
        ('connect-servers', str(NETWORK_ID), '--server', '17', '--server', '18:10.0.0.5'),
        FakeRequest('POST', CONNECT_SERVERS_PATH, {
            'nics': [{'server_id': 17, 'ip': None}, {'server_id': 18, 'ip': '10.0.0.5'}],
            'force_customization': False,
        }),
    ),
)

# Не переданные `--enabled/--disabled` и `--default-action` publisher оставляет
# в текущем значении — команда обязана донести это как `null`, а не как «выключить».
_EDGE_CASES = (
    (
        ('set-bandwidth', str(NETWORK_ID), '--bandwidth', '500'),
        FakeRequest('PUT', EDGE_BANDWIDTH_PATH, {'bandwidth_mbps': 500}),
    ),
    (
        (
            'upsert-nat-rule', str(NETWORK_ID),
            '--type', 'DNAT', '--protocol', 'Tcp',
            '--original-ip', '203.0.113.1', '--translated-ip', '10.0.0.1',
            '--translated-port', '443',
        ),
        FakeRequest('POST', EDGE_NAT_PATH, {
            'rule_id': None,
            'type': 'DNAT',
            'description': None,
            'protocol': 'Tcp',
            'original_ip': '203.0.113.1',
            'original_port': None,
            'translated_ip': '10.0.0.1',
            'translated_port': '443',
            'enabled': None,
        }),
    ),
    (
        (
            'upsert-nat-rule', str(NETWORK_ID), '--rule-id', '7',
            '--type', 'SNAT', '--protocol', 'Any',
            '--original-ip', '10.0.0.1', '--translated-ip', '203.0.113.1', '--disabled',
        ),
        FakeRequest('POST', EDGE_NAT_PATH, {
            'rule_id': 7,
            'type': 'SNAT',
            'description': None,
            'protocol': 'Any',
            'original_ip': '10.0.0.1',
            'original_port': None,
            'translated_ip': '203.0.113.1',
            'translated_port': None,
            'enabled': False,
        }),
    ),
    (
        (
            'upsert-nat-rule', str(NETWORK_ID),
            '--type', 'DNAT', '--protocol', 'Tcp', '--translated-ip', '10.0.0.1',
        ),
        FakeRequest('POST', EDGE_NAT_PATH, {
            'rule_id': None,
            'type': 'DNAT',
            'description': None,
            'protocol': 'Tcp',
            'original_ip': 'any',
            'original_port': None,
            'translated_ip': '10.0.0.1',
            'translated_port': None,
            'enabled': None,
        }),
    ),
    (
        ('upsert-vpn-tunnel', str(NETWORK_ID)) + _VPN_ARGS,
        FakeRequest('POST', EDGE_VPN_PATH, dict(_VPN_PAYLOAD, tunnel_id=None)),
    ),
    (
        ('upsert-vpn-tunnel', str(NETWORK_ID), '--tunnel-id', '3') + _VPN_ARGS,
        FakeRequest('POST', EDGE_VPN_PATH, dict(_VPN_PAYLOAD, tunnel_id=3)),
    ),
)

# Второй адрес правила платформа за пользователя не подставляет: у SNAT это original_ip,
# у DNAT — translated_ip.
_MISSING_ADDRESS_CASES = (
    (('--type', 'SNAT', '--translated-ip', '203.0.113.1'), '--original-ip'),
    (('--type', 'DNAT', '--original-ip', '203.0.113.1'), '--translated-ip'),
)

_FIREWALL_STATE_CASES = (
    ((), {'enabled': None, 'default_action': None}),
    (('--enabled', '--default-action', 'Deny'), {'enabled': True, 'default_action': 'Deny'}),
)


def _invoke(group: str, *args):
    return CliRunner().invoke(entry_point, ('-k', APIKEY, 'vmware', group) + args)


@pytest.mark.parametrize('command_args,expected_request', _NETWORK_CASES)
def test_network_command_options_reach_the_fields_of_the_contract(
    cli_http_client, command_args, expected_request,
):
    cli_http_client.on(expected_request.method, expected_request.path, {'task_id': 'vmw11'})

    result = _invoke('network', *command_args)

    assert result.exit_code == 0, result.output
    assert cli_http_client.requests == [expected_request]


def test_rename_sends_the_new_name_alone(cli_http_client):
    cli_http_client.on('PUT', NETWORK_PATH, {'task_id': 'vmw12'})

    result = _invoke('network', 'rename', str(NETWORK_ID), '--name', 'renamed')

    assert result.exit_code == 0, result.output
    edit_request = cli_http_client.requests[-1]
    # Тело правки сети — подмножество полей DTO, и обязательное имя в нём есть:
    # опущенная полоса означает «оставить как есть», а не «сбросить».
    assert EDIT_NETWORK_REQUIRED_FIELDS <= set(edit_request.payload)
    assert edit_request == FakeRequest('PUT', NETWORK_PATH, {'name': 'renamed'})


def test_set_bandwidth_carries_the_required_name_of_the_current_network(cli_http_client):
    cli_http_client.on('GET', NETWORK_PATH, {'network': NETWORK_ENTITY})
    cli_http_client.on('PUT', NETWORK_PATH, {'task_id': 'vmw13'})

    result = _invoke('network', 'set-bandwidth', str(NETWORK_ID), '--bandwidth', '200')

    assert result.exit_code == 0, result.output
    edit_request = cli_http_client.requests[-1]
    # Дефект C1: тело без обязательного имени давало 400 на любом вызове. Имя команда
    # не спрашивает у пользователя и не выдумывает — берёт текущее из прочитанной сети.
    assert EDIT_NETWORK_REQUIRED_FIELDS <= set(edit_request.payload)
    assert edit_request == FakeRequest('PUT', NETWORK_PATH, {
        'name': NETWORK_ENTITY['name'],
        'bandwidth_mbps': 200,
    })


@pytest.mark.parametrize('command_args,expected_request', _EDGE_CASES)
def test_edge_command_options_reach_the_fields_of_the_contract(
    cli_http_client, command_args, expected_request,
):
    cli_http_client.on(expected_request.method, expected_request.path, {'task_id': 'vmw14'})

    result = _invoke('edge', *command_args)

    assert result.exit_code == 0, result.output
    assert cli_http_client.requests == [expected_request]


@pytest.mark.parametrize('state_args,expected_state', _FIREWALL_STATE_CASES)
def test_replace_firewall_leaves_the_state_untouched_unless_it_is_given(
    cli_http_client, rules_file, state_args, expected_state,
):
    cli_http_client.on('PUT', EDGE_FIREWALL_PATH, {'task_id': 'vmw15'})

    result = _invoke(
        'edge', 'replace-firewall', str(NETWORK_ID),
        '--rules-file', rules_file([FIREWALL_RULE]), *state_args,
    )

    assert result.exit_code == 0, result.output
    assert cli_http_client.requests == [FakeRequest('PUT', EDGE_FIREWALL_PATH, dict(
        expected_state, rules=[FIREWALL_RULE],
    ))]


@pytest.mark.parametrize('rule_args,named_option', _MISSING_ADDRESS_CASES)
def test_nat_rule_without_the_address_the_platform_never_supplies_is_refused(
    cli_http_client, rule_args, named_option,
):
    result = _invoke('edge', 'upsert-nat-rule', str(NETWORK_ID), '--protocol', 'Tcp', *rule_args)

    assert result.exit_code == _USAGE_ERROR_EXIT_CODE
    # Отказывает сама команда, а не click отсутствующей опцией: адрес обязателен
    # у одного типа правила и не нужен у другого.
    assert '{option} is required'.format(option=named_option) in result.output
    assert cli_http_client.requests == []
