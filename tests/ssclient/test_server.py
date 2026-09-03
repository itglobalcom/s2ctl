from ssclient.server.server import ServerService, VolumeCreationData
from ssclient.task_entities import TaskState
from tests.conftest import task_response


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
