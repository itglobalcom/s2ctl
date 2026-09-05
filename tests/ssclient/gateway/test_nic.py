from ssclient.gateway.nic import GatewayNicService
from ssclient.network.network_id import NetworkId
from ssclient.task_entities import TaskState
from tests.conftest import FakeRequest, task_response
from tests.ssclient.gateway.coordinates import GATEWAY_PATH

NICS_PATH = '{gateway_path}/nics'.format(gateway_path=GATEWAY_PATH)
NIC_PATH = '{nics_path}/7'.format(nics_path=NICS_PATH)


def _network_id(raw_id: str) -> NetworkId:
    network_id = NetworkId.try_parse(raw_id)
    assert network_id is not None
    return network_id


async def test_create_posts_network_id_and_returns_task_without_wait(
    fake_http_client, gateway_id,
):
    fake_http_client.on('POST', NICS_PATH, {'task_id': 'l1t345'})

    task_wrap = await GatewayNicService(fake_http_client, gateway_id).create(
        network_id=_network_id('l1n3'),
    )

    assert fake_http_client.requests == [
        FakeRequest('POST', NICS_PATH, {'network_id': 'l1n3'}),
    ]
    assert task_wrap == {'task_id': 'l1t345'}


async def test_create_with_wait_polls_task_and_returns_nothing(fake_http_client, gateway_id):
    fake_http_client.on('POST', NICS_PATH, {'task_id': 'l1t345'})
    fake_http_client.on('GET', 'api/v1/tasks/l1t345', task_response('l1t345', TaskState.completed))

    task_wrap = await GatewayNicService(fake_http_client, gateway_id).create(
        network_id=_network_id('l1n3'), wait=True,
    )

    assert fake_http_client.paths('GET') == ['api/v1/tasks/l1t345']
    assert task_wrap is None


async def test_delete_without_wait_returns_task_of_the_deletion(fake_http_client, gateway_id):
    # Как и у самого шлюза: без `return_task=true` publisher не отдаёт ссылку на задачу.
    delete_path = '{path}?return_task=true'.format(path=NIC_PATH)
    fake_http_client.on('DELETE', delete_path, {'task_id': 'l1t346'})

    task_wrap = await GatewayNicService(fake_http_client, gateway_id).delete(7)

    assert fake_http_client.requests == [FakeRequest('DELETE', delete_path)]
    assert task_wrap == {'task_id': 'l1t346'}


async def test_delete_with_wait_polls_the_same_task(fake_http_client, gateway_id):
    delete_path = '{path}?return_task=true'.format(path=NIC_PATH)
    fake_http_client.on('DELETE', delete_path, {'task_id': 'l1t346'})
    fake_http_client.on('GET', 'api/v1/tasks/l1t346', task_response('l1t346', TaskState.completed))

    task_wrap = await GatewayNicService(fake_http_client, gateway_id).delete(7, wait=True)

    assert fake_http_client.requests[0] == FakeRequest('DELETE', delete_path)
    assert fake_http_client.paths('GET') == ['api/v1/tasks/l1t346']
    assert task_wrap is None
