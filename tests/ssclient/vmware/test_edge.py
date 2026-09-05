import pytest

from ssclient.task_entities import TaskState
from ssclient.vmware.edge import (
    VmwareEdgeNatService,
    VmwareEdgeService,
    VmwareEdgeVpnService,
)
from tests.conftest import FakeRequest, task_response
from tests.ssclient.vmware.conftest import EDGE_PATH, NETWORK_ID

BANDWIDTH_PATH = '{edge}/bandwidth'.format(edge=EDGE_PATH)
FIREWALL_PATH = '{edge}/firewall'.format(edge=EDGE_PATH)
NAT_PATH = '{edge}/nat'.format(edge=EDGE_PATH)
VPN_PATH = '{edge}/vpn'.format(edge=EDGE_PATH)

FIREWALL_RULE = {
    'enabled': True,
    'name': 'ssh',
    'description': '',
    'action': 'Allow',
    'protocol': 'Tcp',
    'source': '0.0.0.0/0',
    'source_port': 'any',
    'destination': '10.0.0.1',
    'destination_port': '22',
}

FIREWALL_ENTITY = {'enabled': True, 'default_action': 'Deny', 'rules': [FIREWALL_RULE]}

NAT_RULE_ENTITY = {
    'id': 7,
    'vcloud_id': 'urn:nat:7',
    'description': '',
    'type': 'DNAT',
    'original_ip': '203.0.113.1',
    'translated_ip': '10.0.0.1',
    'protocol': 'Tcp',
    'original_port': '443',
    'translated_port': '443',
    'enabled': True,
}

VPN_ENTITY = {'enabled': True, 'tunnels': []}

# Правило и туннель — самостоятельные ресурсы edge: удаление адресует конкретный id,
# а не переписывает набор целиком.
DELETE_CASES = (
    (VmwareEdgeNatService, 'delete_rule', 7, '{path}/7'.format(path=NAT_PATH)),
    (VmwareEdgeVpnService, 'delete_tunnel', 9, '{path}/9'.format(path=VPN_PATH)),
)


def _edge(fake_http_client) -> VmwareEdgeService:
    return VmwareEdgeService(fake_http_client, NETWORK_ID)


async def test_set_bandwidth_puts_own_subresource_and_returns_task(fake_http_client):
    fake_http_client.on('PUT', BANDWIDTH_PATH, {'task_id': 'vmw910'})

    task_wrap = await _edge(fake_http_client).set_bandwidth(bandwidth_mbps=200)

    # Канал шлюза меняется своим подресурсом, а не тем же PUT, что имя сети.
    assert fake_http_client.requests == [
        FakeRequest('PUT', BANDWIDTH_PATH, {'bandwidth_mbps': 200}),
    ]
    assert task_wrap == {'task_id': 'vmw910'}


async def test_get_firewall_unwraps_firewall(fake_http_client):
    fake_http_client.on('GET', FIREWALL_PATH, {'firewall': FIREWALL_ENTITY})

    firewall = await _edge(fake_http_client).firewall().get()

    assert fake_http_client.paths('GET') == [FIREWALL_PATH]
    assert firewall == FIREWALL_ENTITY


async def test_update_firewall_puts_whole_rule_set(fake_http_client):
    fake_http_client.on('PUT', FIREWALL_PATH, {'task_id': 'vmw911'})

    task_wrap = await _edge(fake_http_client).firewall().update(
        rules=[FIREWALL_RULE], enabled=True, default_action='Deny',
    )

    assert fake_http_client.requests == [FakeRequest('PUT', FIREWALL_PATH, {
        'enabled': True,
        'default_action': 'Deny',
        'rules': [FIREWALL_RULE],
    })]
    assert task_wrap == {'task_id': 'vmw911'}


async def test_update_firewall_with_wait_survives_response_without_task(fake_http_client):
    # Правку без фактических изменений publisher закрывает 204 без тела: задачи нет,
    # ждать нечего — операция обязана дочитать firewall, а не упасть.
    fake_http_client.on('PUT', FIREWALL_PATH, None)
    fake_http_client.on('GET', FIREWALL_PATH, {'firewall': FIREWALL_ENTITY})

    firewall = await _edge(fake_http_client).firewall().update(rules=[FIREWALL_RULE], wait=True)

    assert fake_http_client.paths('GET') == [FIREWALL_PATH]
    assert firewall == FIREWALL_ENTITY


async def test_get_nat_unwraps_rules(fake_http_client):
    fake_http_client.on('GET', NAT_PATH, {'rules': [NAT_RULE_ENTITY]})

    rules = await _edge(fake_http_client).nat().get()

    assert fake_http_client.paths('GET') == [NAT_PATH]
    assert rules == [NAT_RULE_ENTITY]


@pytest.mark.parametrize('rule_id,optional_fields,expected_optional', (
    (
        7,
        {
            'original_port': '443',
            'translated_port': '443',
            'description': 'web',
            'enabled': True,
        },
        {
            'original_port': '443',
            'translated_port': '443',
            'description': 'web',
            'enabled': True,
        },
    ),
    (
        None,
        {},
        {
            'original_port': None,
            'translated_port': None,
            'description': None,
            'enabled': None,
        },
    ),
))
async def test_upsert_nat_rule_posts_whole_rule(
    fake_http_client, rule_id, optional_fields, expected_optional,
):
    fake_http_client.on('POST', NAT_PATH, {'task_id': 'vmw912'})

    task_wrap = await _edge(fake_http_client).nat().upsert_rule(
        rule_id=rule_id,
        rule_type='DNAT',
        protocol='Tcp',
        original_ip='203.0.113.1',
        translated_ip='10.0.0.1',
        **optional_fields,
    )

    # Операция над одним правилом: `rule_id` выбирает изменяемое, без него правило создаётся.
    expected_payload = {
        'rule_id': rule_id,
        'type': 'DNAT',
        'protocol': 'Tcp',
        'original_ip': '203.0.113.1',
        'translated_ip': '10.0.0.1',
    }
    expected_payload.update(expected_optional)
    assert fake_http_client.requests == [FakeRequest('POST', NAT_PATH, expected_payload)]
    assert task_wrap == {'task_id': 'vmw912'}


async def test_upsert_nat_rule_leaves_the_address_of_the_platform_to_the_platform(fake_http_client):
    fake_http_client.on('POST', NAT_PATH, {'task_id': 'vmw914'})

    await _edge(fake_http_client).nat().upsert_rule(
        rule_type='DNAT', protocol='Tcp', translated_ip='10.0.0.1',
    )

    # Пустой адрес publisher не принимает, а `any` для него — «подставь сам»: в original_ip
    # DNAT-правила он всё равно запишет внешний адрес edge.
    assert fake_http_client.requests[-1].payload['original_ip'] == 'any'


async def test_get_vpn_unwraps_vpn(fake_http_client):
    fake_http_client.on('GET', VPN_PATH, {'vpn': VPN_ENTITY})

    vpn = await _edge(fake_http_client).vpn().get()

    assert fake_http_client.paths('GET') == [VPN_PATH]
    assert vpn == VPN_ENTITY


async def test_upsert_vpn_tunnel_posts_whole_tunnel(fake_http_client):
    fake_http_client.on('POST', VPN_PATH, {'task_id': 'vmw913'})

    task_wrap = await _edge(fake_http_client).vpn().upsert_tunnel(
        tunnel_id=9,
        name='to-office',
        shared_key='secret',
        peer_network='192.168.0.0/24',
        peer_endpoint='198.51.100.1',
        peer_identificator='198.51.100.1',
        mtu=1500,
        encryption_type='Aes256',
        diffie_hellman_group='DH14',
        enabled=True,
        perfect_forward_secrecy=False,
    )

    # Операция над одним туннелем: `tunnel_id` выбирает изменяемый, без него туннель создаётся.
    assert fake_http_client.requests == [FakeRequest('POST', VPN_PATH, {
        'tunnel_id': 9,
        'name': 'to-office',
        'enabled': True,
        'mtu': 1500,
        'encryption_type': 'Aes256',
        'shared_key': 'secret',
        'peer_network': '192.168.0.0/24',
        'peer_endpoint': '198.51.100.1',
        'peer_identificator': '198.51.100.1',
        'perfect_forward_secrecy': False,
        'diffie_hellman_group': 'DH14',
    })]
    assert task_wrap == {'task_id': 'vmw913'}


@pytest.mark.parametrize('service_class,method_name,entity_id,expected_path', DELETE_CASES)
async def test_delete_addresses_single_entity_and_polls_task(
    fake_http_client, service_class, method_name, entity_id, expected_path,
):
    fake_http_client.on('DELETE', expected_path, {'task_id': 'vmw914'})
    fake_http_client.on('GET', 'api/v1/tasks/vmw914', task_response('vmw914', TaskState.completed))

    delete = getattr(service_class(fake_http_client, NETWORK_ID), method_name)
    task_wrap = await delete(entity_id, wait=True)

    # Удаление адресует ресурс id и не требует `return_task=true`.
    assert fake_http_client.requests[0] == FakeRequest('DELETE', expected_path)
    assert fake_http_client.paths('GET') == ['api/v1/tasks/vmw914']
    assert task_wrap is None
