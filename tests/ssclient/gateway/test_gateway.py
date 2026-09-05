import pytest

from ssclient.gateway.gateway import GatewayService
from ssclient.network.network_id import NetworkId
from ssclient.task_entities import TaskState
from tests.conftest import FakeRequest, task_response
from tests.ssclient.gateway.coordinates import GATEWAY_PATH, GATEWAYS_PATH

BANDWIDTH_PATH = '{gateway_path}/bandwidth'.format(gateway_path=GATEWAY_PATH)

GATEWAY_ENTITY = {
    'id': 'l1e2',
    'location_id': 'l1',
    'name': 'edge',
    'nics': [],
    'nat_rules': [],
    'firewall_rules': [],
    'state': 'Active',
    'powered_on': True,
    'created': '2026-09-01T00:00:00',
    'tags': [],
}


def _network_id(raw_id: str) -> NetworkId:
    network_id = NetworkId.try_parse(raw_id)
    assert network_id is not None
    return network_id


@pytest.mark.parametrize('location_id,expected_path', (
    (None, GATEWAYS_PATH),
    ('l1', '{path}?location_id=l1'.format(path=GATEWAYS_PATH)),
))
async def test_list_unwraps_gateways_and_filters_by_location(
    fake_http_client, location_id, expected_path,
):
    fake_http_client.on('GET', expected_path, {'gateways': [GATEWAY_ENTITY]})

    gateways = await GatewayService(fake_http_client).list(location_id=location_id)

    assert fake_http_client.paths('GET') == [expected_path]
    assert gateways == [GATEWAY_ENTITY]


async def test_create_posts_gateway_and_returns_task_without_wait(fake_http_client):
    fake_http_client.on('POST', GATEWAYS_PATH, {'task_id': 'l1t345'})

    task_wrap = await GatewayService(fake_http_client).create(
        location_id='l1',
        name='edge',
        bandwidth_mbps=100,
        network_ids=[_network_id('l1n3'), _network_id('l1n4')],
    )

    # Доменный тип на границе сериализации разворачивается в строку контракта.
    assert fake_http_client.requests == [FakeRequest('POST', GATEWAYS_PATH, {
        'location_id': 'l1',
        'name': 'edge',
        'bandwidth_mbps': 100,
        'network_ids': ['l1n3', 'l1n4'],
    })]
    assert task_wrap == {'task_id': 'l1t345'}


async def test_create_with_wait_reads_gateway_addressed_by_task_resources(fake_http_client):
    fake_http_client.on('POST', GATEWAYS_PATH, {'task_id': 'l1t345'})
    fake_http_client.on(
        'GET', 'api/v1/tasks/l1t345',
        task_response('l1t345', TaskState.completed, resources=[
            ('network', 'l1n3'), ('gateway', 'l1e5'),
        ]),
    )
    fake_http_client.on('GET', 'api/v1/gateways/l1e5', {'gateway': GATEWAY_ENTITY})

    gateway = await GatewayService(fake_http_client).create(
        location_id='l1',
        name='edge',
        bandwidth_mbps=None,
        network_ids=[_network_id('l1n3')],
        wait=True,
    )

    # Id созданного шлюза известен только из resources[] задачи, причём по типу `gateway`,
    # а не по порядку записей.
    assert fake_http_client.paths('GET') == ['api/v1/tasks/l1t345', 'api/v1/gateways/l1e5']
    assert gateway == GATEWAY_ENTITY


async def test_get_reads_gateway_by_composite_id(fake_http_client, gateway_id):
    fake_http_client.on('GET', GATEWAY_PATH, {'gateway': GATEWAY_ENTITY})

    gateway = await GatewayService(fake_http_client).get(gateway_id)

    assert fake_http_client.paths('GET') == [GATEWAY_PATH]
    assert gateway == GATEWAY_ENTITY


async def test_rename_puts_name_and_unwraps_gateway(fake_http_client, gateway_id):
    fake_http_client.on('PUT', GATEWAY_PATH, {'gateway': GATEWAY_ENTITY})

    gateway = await GatewayService(fake_http_client).rename(gateway_id, name='edge')

    assert fake_http_client.requests == [FakeRequest('PUT', GATEWAY_PATH, {'name': 'edge'})]
    assert gateway == GATEWAY_ENTITY


async def test_set_bandwidth_puts_subresource_and_returns_task_without_wait(
    fake_http_client, gateway_id,
):
    fake_http_client.on('PUT', BANDWIDTH_PATH, {'task_id': 'l1t346'})

    task_wrap = await GatewayService(fake_http_client).set_bandwidth(
        gateway_id, bandwidth_mbps=200,
    )

    # Канал меняется отдельным подресурсом, а не тем же PUT, что переименование.
    assert fake_http_client.requests == [
        FakeRequest('PUT', BANDWIDTH_PATH, {'bandwidth_mbps': 200}),
    ]
    assert task_wrap == {'task_id': 'l1t346'}


async def test_set_bandwidth_with_wait_rereads_known_gateway(fake_http_client, gateway_id):
    fake_http_client.on('PUT', BANDWIDTH_PATH, {'task_id': 'l1t346'})
    fake_http_client.on('GET', 'api/v1/tasks/l1t346', task_response('l1t346', TaskState.completed))
    fake_http_client.on('GET', GATEWAY_PATH, {'gateway': GATEWAY_ENTITY})

    gateway = await GatewayService(fake_http_client).set_bandwidth(
        gateway_id, bandwidth_mbps=200, wait=True,
    )

    # Id шлюза — вход операции, поэтому после задачи читается он, а не resources[].
    assert fake_http_client.paths('GET') == ['api/v1/tasks/l1t346', GATEWAY_PATH]
    assert gateway == GATEWAY_ENTITY


async def test_delete_without_wait_returns_task_of_the_deletion(fake_http_client, gateway_id):
    # Ссылку на задачу publisher отдаёт только по `return_task=true`: без параметра
    # ответ пуст и печатать команде нечего.
    delete_path = '{path}?return_task=true'.format(path=GATEWAY_PATH)
    fake_http_client.on('DELETE', delete_path, {'task_id': 'l1t347'})

    task_wrap = await GatewayService(fake_http_client).delete(gateway_id)

    assert fake_http_client.requests == [FakeRequest('DELETE', delete_path)]
    assert task_wrap == {'task_id': 'l1t347'}


async def test_delete_with_wait_polls_the_same_task(fake_http_client, gateway_id):
    delete_path = '{path}?return_task=true'.format(path=GATEWAY_PATH)
    fake_http_client.on('DELETE', delete_path, {'task_id': 'l1t347'})
    fake_http_client.on('GET', 'api/v1/tasks/l1t347', task_response('l1t347', TaskState.completed))

    task_wrap = await GatewayService(fake_http_client).delete(gateway_id, wait=True)

    assert fake_http_client.requests[0] == FakeRequest('DELETE', delete_path)
    assert fake_http_client.paths('GET') == ['api/v1/tasks/l1t347']
    assert task_wrap is None
