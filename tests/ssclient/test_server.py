import pytest

from ssclient.network.network_id import NetworkId
from ssclient.server.nic import NicService
from ssclient.server.server import ServerService, VolumeCreationData
from ssclient.task_entities import TaskState
from tests.conftest import FakeHttpClient, FakeRequest, task_response


async def test_create_with_wait_returns_server_addressed_by_task_resources(fake_http_client):
    fake_http_client.on('POST', 'api/v1/servers', {'task_id': 'l2t345'})
    fake_http_client.on(
        'GET', 'api/v1/tasks/l2t345',
        task_response('l2t345', TaskState.completed, resources=[('server', 'l2s99')]),
    )
    fake_http_client.on('GET', 'api/v1/servers/l2s99', {'server': {'id': 'l2s99', 'name': 'srv'}})

    server = await ServerService(fake_http_client).create(
        name='srv',
        location_id='l2',
        image_id='img',
        cpu=1,
        ram_mb=1024,
        volumes=[VolumeCreationData('boot', 10240)],
        networks=[100],
        ssh_key_ids=[],
        wait=True,
    )

    assert server['id'] == 'l2s99'
    assert fake_http_client.paths('GET') == ['api/v1/tasks/l2t345', 'api/v1/servers/l2s99']


async def test_set_configuration_puts_whole_configuration_and_reads_known_server(fake_http_client):
    fake_http_client.on('PUT', 'api/v1/servers/l2s99', {'task_id': 'l2t345'})
    fake_http_client.on('GET', 'api/v1/tasks/l2t345', task_response('l2t345', TaskState.completed))
    fake_http_client.on(
        'GET', 'api/v1/servers/l2s99', {'server': {'id': 'l2s99', 'cpu': 4, 'ram_mb': 8192}},
    )

    server = await ServerService(fake_http_client).set_configuration(
        'l2s99', cpu=4, ram_mb=8192, wait=True,
    )

    assert fake_http_client.requests[0] == FakeRequest(
        'PUT', 'api/v1/servers/l2s99', {'cpu': 4, 'ram_mb': 8192},
    )
    assert server['cpu'] == 4
    # id сервера — вход операции, поэтому после задачи читается он, а не resources[].
    assert fake_http_client.paths('GET') == ['api/v1/tasks/l2t345', 'api/v1/servers/l2s99']


async def test_rename_puts_name_subresource_and_returns_task_without_wait(fake_http_client):
    fake_http_client.on('PUT', 'api/v1/servers/l2s99/name', {'task_id': 'l2t346'})

    task_wrap = await ServerService(fake_http_client).rename('l2s99', name='new-name')

    assert fake_http_client.requests == [
        FakeRequest('PUT', 'api/v1/servers/l2s99/name', {'name': 'new-name'}),
    ]
    assert task_wrap == {'task_id': 'l2t346'}


async def test_set_configuration_and_update_stay_different_operations(fake_http_client):
    """PUT задаёт конфигурацию целиком, PATCH меняет отдельные поля — разные юзкейсы publisher'а."""
    put_client = fake_http_client
    put_client.on('PUT', 'api/v1/servers/l2s99', {'task_id': 'l2t345'})
    patch_client = FakeHttpClient()
    patch_client.on('PATCH', 'api/v1/servers/l2s99', {'task_id': 'l2t346'})

    await ServerService(put_client).set_configuration('l2s99', cpu=4, ram_mb=8192)
    await ServerService(patch_client).update('l2s99', cpu=4, wait=False)

    assert [request.method for request in put_client.requests] == ['PUT']
    assert [request.method for request in patch_client.requests] == ['PATCH']
    assert patch_client.requests[0].payload == {'cpu': 4}


async def test_nic_update_puts_bandwidth_and_reads_known_nic(fake_http_client):
    fake_http_client.on('PUT', 'api/v1/servers/l2s99/nics/7', {'task_id': 'l2t345'})
    fake_http_client.on('GET', 'api/v1/tasks/l2t345', task_response('l2t345', TaskState.completed))
    fake_http_client.on(
        'GET', 'api/v1/servers/l2s99/nics/7', {'nic': {'id': 7, 'bandwidth_mbps': 200}},
    )

    nic = await NicService(fake_http_client, 'l2s99').update(7, bandwidth_mbps=200, wait=True)

    assert fake_http_client.requests[0] == FakeRequest(
        'PUT', 'api/v1/servers/l2s99/nics/7', {'bandwidth_mbps': 200},
    )
    assert nic['bandwidth_mbps'] == 200
    assert fake_http_client.paths('GET') == [
        'api/v1/tasks/l2t345', 'api/v1/servers/l2s99/nics/7',
    ]


async def test_add_nic_with_wait_reads_nic_from_task_resources(fake_http_client):
    fake_http_client.on('POST', 'api/v1/servers/l2s99/nics', {'task_id': 'l2t347'})
    fake_http_client.on(
        'GET', 'api/v1/tasks/l2t347',
        task_response('l2t347', TaskState.completed, resources=[
            ('server', 'l2s99'), ('nic', '7'),
        ]),
    )
    fake_http_client.on('GET', 'api/v1/servers/l2s99/nics/7', {'nic': {'id': 7}})

    nic = await NicService(fake_http_client, 'l2s99').create(
        network_id=NetworkId('l1n3'), bandwidth=None, wait=True,
    )

    # Интерфейс берётся по типу ресурса, а не по первой записи `resources[]`.
    assert fake_http_client.paths('GET') == [
        'api/v1/tasks/l2t347', 'api/v1/servers/l2s99/nics/7',
    ]
    assert nic == {'id': 7}


@pytest.mark.parametrize('network_id,expected_field', (
    (NetworkId('l1n3'), 'l1n3'),
    # Сеть у интерфейса необязательна: без неё publisher подключает публичную,
    # и на проводе обязан остаться `null`, а не отсутствующее поле.
    (None, None),
))
async def test_add_nic_sends_network_id_as_contract_string(
    fake_http_client, network_id, expected_field,
):
    fake_http_client.on('POST', 'api/v1/servers/l2s99/nics', {'task_id': 'l2t345'})

    await NicService(fake_http_client, 'l2s99').create(network_id=network_id, bandwidth=100)

    assert fake_http_client.requests == [FakeRequest('POST', 'api/v1/servers/l2s99/nics', {
        'network_id': expected_field,
        'bandwidth_mbps': 100,
    })]


# Ссылку на задачу удаления publisher отдаёт только по `return_task=true`: без него
# ответ пуст, и дождаться удаления скрипту нечем. У сервера id задачи приходит
# в форме без части локации (`lt{id}`) — реестр форматов её принимает.
async def test_delete_asks_the_publisher_for_the_reference_to_the_task(fake_http_client):
    expected_path = 'api/v1/servers/l2s99?return_task=true'
    fake_http_client.on('DELETE', expected_path, {'task_id': 'lt345'})

    task_wrap = await ServerService(fake_http_client).delete('l2s99')

    assert fake_http_client.requests == [FakeRequest('DELETE', expected_path)]
    assert task_wrap == {'task_id': 'lt345'}


async def test_delete_with_wait_polls_the_task_of_the_deletion(fake_http_client):
    fake_http_client.on('DELETE', 'api/v1/servers/l2s99?return_task=true', {'task_id': 'lt345'})
    fake_http_client.on('GET', 'api/v1/tasks/lt345', task_response('lt345', TaskState.completed))

    task_wrap = await ServerService(fake_http_client).delete('l2s99', wait=True)

    assert fake_http_client.paths('GET') == ['api/v1/tasks/lt345']
    assert task_wrap is None


async def test_delete_nic_asks_the_publisher_for_the_reference_to_the_task(fake_http_client):
    expected_path = 'api/v1/servers/l2s99/nics/7?return_task=true'
    fake_http_client.on('DELETE', expected_path, {'task_id': 'l2t345'})
    fake_http_client.on('GET', 'api/v1/tasks/l2t345', task_response('l2t345', TaskState.completed))

    task_wrap = await NicService(fake_http_client, 'l2s99').delete(7, wait=True)

    assert fake_http_client.paths('DELETE') == [expected_path]
    assert fake_http_client.paths('GET') == ['api/v1/tasks/l2t345']
    assert task_wrap is None
