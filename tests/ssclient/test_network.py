import pytest

from ssclient.network.network import NetworkService
from ssclient.network.network_id import NetworkId
from ssclient.task_entities import TaskState
from tests.conftest import FakeRequest, task_response

NETWORKS_PATH = 'api/v1/networks/isolated'
NETWORK_PATH = '{path}/l1n3'.format(path=NETWORKS_PATH)
TAGS_PATH = '{path}/tags'.format(path=NETWORK_PATH)

# Маршрут publisher'а — `l{location_id}n{network_id}`: части обязательны, порядок закреплён,
# перепутанные местами части (`n1l3`) — мусор.
ID_FORMATS = (
    ('l1n3', 'l1n3'),
    ('l12n345', 'l12n345'),
    ('n1l3', None),
    ('l1n', None),
    ('ln3', None),
    ('l1e3', None),
    ('l1n3x', None),
    ('garbage', None),
    ('', None),
)

NETWORK_ENTITY = {
    'id': 'l1n3',
    'location_id': 'l1',
    'name': 'internal',
    'description': 'office',
}


def _network_id(raw_id: str) -> NetworkId:
    network_id = NetworkId.try_parse(raw_id)
    assert network_id is not None
    return network_id


@pytest.mark.parametrize('raw_id,expected_value', ID_FORMATS)
def test_composite_id_is_parsed_only_in_publisher_format(raw_id, expected_value):
    network_id = NetworkId.try_parse(raw_id)

    if expected_value is None:
        assert network_id is None
    else:
        assert network_id is not None
        assert network_id.value == expected_value


async def test_get_reads_network_by_composite_id(fake_http_client):
    fake_http_client.on('GET', NETWORK_PATH, {'isolated_network': NETWORK_ENTITY})

    network = await NetworkService(fake_http_client).get(_network_id('l1n3'))

    assert fake_http_client.paths('GET') == [NETWORK_PATH]
    assert network == NETWORK_ENTITY


async def test_update_puts_name_and_description(fake_http_client):
    fake_http_client.on('PUT', NETWORK_PATH, {'task_id': 'l1t345'})

    task_wrap = await NetworkService(fake_http_client).update(
        _network_id('l1n3'), name='internal', description='office',
    )

    assert fake_http_client.requests == [FakeRequest('PUT', NETWORK_PATH, {
        'name': 'internal',
        'description': 'office',
    })]
    assert task_wrap == {'task_id': 'l1t345'}


async def test_delete_asks_the_publisher_for_the_reference_to_the_task(fake_http_client):
    # Без `return_task=true` ответ удаления пуст, и `--wait` нечего ждать.
    expected_path = '{path}?return_task=true'.format(path=NETWORK_PATH)
    fake_http_client.on('DELETE', expected_path, {'task_id': 'l1t345'})

    task_wrap = await NetworkService(fake_http_client).delete(_network_id('l1n3'))

    assert fake_http_client.requests == [FakeRequest('DELETE', expected_path)]
    assert task_wrap == {'task_id': 'l1t345'}


async def test_delete_with_wait_polls_the_task_of_the_deletion(fake_http_client):
    expected_path = '{path}?return_task=true'.format(path=NETWORK_PATH)
    fake_http_client.on('DELETE', expected_path, {'task_id': 'l1t345'})
    fake_http_client.on('GET', 'api/v1/tasks/l1t345', task_response('l1t345', TaskState.completed))

    task_wrap = await NetworkService(fake_http_client).delete(_network_id('l1n3'), wait=True)

    assert fake_http_client.paths('GET') == ['api/v1/tasks/l1t345']
    assert task_wrap is None


async def test_create_with_wait_reads_network_addressed_by_task_resources(fake_http_client):
    fake_http_client.on('POST', NETWORKS_PATH, {'task_id': 'l1t345'})
    fake_http_client.on(
        'GET', 'api/v1/tasks/l1t345',
        task_response('l1t345', TaskState.completed, resources=[('network', 'l1n9')]),
    )
    fake_http_client.on(
        'GET', '{path}/l1n9'.format(path=NETWORKS_PATH), {'isolated_network': NETWORK_ENTITY},
    )

    network = await NetworkService(fake_http_client).create(
        location_id='l1',
        name='internal',
        description='office',
        network_prefix='10.0.0.0',
        mask=24,
        wait=True,
    )

    # Id созданной сети приходит из resources[] строкой контракта, а не доменным типом:
    # чтение по нему обязано остаться доступным изнутри сервиса.
    assert fake_http_client.paths('GET') == ['api/v1/tasks/l1t345', '{path}/l1n9'.format(
        path=NETWORKS_PATH,
    )]
    assert network == NETWORK_ENTITY


async def test_tags_send_the_same_paths_as_before_migration(fake_http_client):
    fake_http_client.on('POST', TAGS_PATH, {'value': 'prod'})
    fake_http_client.on('DELETE', '{path}/prod'.format(path=TAGS_PATH), None)
    tag_service = NetworkService(fake_http_client).tags(_network_id('l1n3'))

    await tag_service.create(name='prod')
    await tag_service.delete('prod')

    assert fake_http_client.requests == [
        FakeRequest('POST', TAGS_PATH, {'value': 'prod'}),
        FakeRequest('DELETE', '{path}/prod'.format(path=TAGS_PATH)),
    ]
