"""Диски vStack-сервера: `--wait` адресует диск через `resources[]` задачи.

Регресс на миграцию с legacy-поля `volume_id` задачи на `resources[]`.
"""
from ssclient.server.volume import VolumeService
from ssclient.task_entities import TaskState
from tests.conftest import task_response

VOLUMES_PATH = 'api/v1/servers/l2s99/volumes'
VOLUME_PATH = '{path}/20210'.format(path=VOLUMES_PATH)

VOLUME_ENTITY = {
    'id': 20210,
    'server_id': 'l2s99',
    'name': 'data',
    'size_mb': 25600,
    'created': '2026-09-01T00:00:00',
}


async def test_create_with_wait_reads_volume_from_task_resources(fake_http_client):
    fake_http_client.on('POST', VOLUMES_PATH, {'task_id': 'l2t345'})
    fake_http_client.on(
        'GET', 'api/v1/tasks/l2t345',
        task_response('l2t345', TaskState.completed, resources=[
            ('server', 'l2s99'), ('volume', '20210'),
        ]),
    )
    fake_http_client.on('GET', VOLUME_PATH, {'volume': VOLUME_ENTITY})

    volume = await VolumeService(fake_http_client, 'l2s99').create(
        name='data', size_mb=25600, wait=True,
    )

    # Диск берётся по типу ресурса, а не по первой записи `resources[]`.
    assert fake_http_client.paths('GET') == ['api/v1/tasks/l2t345', VOLUME_PATH]
    assert volume == VOLUME_ENTITY


async def test_update_with_wait_reads_volume_from_task_resources(fake_http_client):
    fake_http_client.on('PUT', VOLUME_PATH, {'task_id': 'l2t346'})
    fake_http_client.on(
        'GET', 'api/v1/tasks/l2t346',
        task_response('l2t346', TaskState.completed, resources=[('volume', '20210')]),
    )
    fake_http_client.on('GET', VOLUME_PATH, {'volume': VOLUME_ENTITY})

    volume = await VolumeService(fake_http_client, 'l2s99').update(
        20210, size_mb=51200, wait=True,
    )

    assert fake_http_client.paths('GET') == ['api/v1/tasks/l2t346', VOLUME_PATH]
    assert volume == VOLUME_ENTITY
