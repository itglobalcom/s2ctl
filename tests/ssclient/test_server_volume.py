"""Диски vStack-сервера: `--wait` адресует диск через `resources[]` задачи.

Регресс на миграцию с legacy-поля `volume_id` задачи на `resources[]`.
"""
from ssclient.server.server_id import ServerId
from ssclient.server.volume import VolumeService
from ssclient.task_entities import TaskState
from tests.conftest import FakeRequest, task_response

SERVER_ID = ServerId('l2s99')
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

    volume = await VolumeService(fake_http_client, SERVER_ID).create(
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

    volume = await VolumeService(fake_http_client, SERVER_ID).update(
        20210, size_mb=51200, wait=True,
    )

    assert fake_http_client.paths('GET') == ['api/v1/tasks/l2t346', VOLUME_PATH]
    assert volume == VOLUME_ENTITY


async def test_update_renames_and_resizes_a_volume_in_one_request(fake_http_client):
    fake_http_client.on('PUT', VOLUME_PATH, {'task_id': 'l2t347'})

    await VolumeService(fake_http_client, SERVER_ID).update(20210, size_mb=51200, name='data')

    # Имя и размер диска publisher меняет одним PUT: `VstackEditVolumeCommand`
    # несёт оба поля, отдельного маршрута переименования у диска нет.
    assert fake_http_client.requests == [FakeRequest('PUT', VOLUME_PATH, {
        'name': 'data',
        'size_mb': 51200,
    })]


async def test_update_without_name_leaves_the_current_one_to_the_publisher(fake_http_client):
    fake_http_client.on('PUT', VOLUME_PATH, {'task_id': 'l2t348'})

    await VolumeService(fake_http_client, SERVER_ID).update(20210, size_mb=51200)

    # `VstackEditVolumeCommand.Name` необязателен, и на `null` publisher оставляет
    # диску текущее имя: подставлять его самому не нужно.
    assert fake_http_client.requests[0].payload == {'name': None, 'size_mb': 51200}


async def test_delete_asks_the_publisher_for_the_reference_to_the_task(fake_http_client):
    # Без `return_task=true` ответ удаления пуст, и `--wait` нечего ждать.
    expected_path = '{path}?return_task=true'.format(path=VOLUME_PATH)
    fake_http_client.on('DELETE', expected_path, {'task_id': 'l2t349'})
    fake_http_client.on('GET', 'api/v1/tasks/l2t349', task_response('l2t349', TaskState.completed))

    task_wrap = await VolumeService(fake_http_client, SERVER_ID).delete(20210, wait=True)

    assert fake_http_client.paths('DELETE') == [expected_path]
    assert fake_http_client.paths('GET') == ['api/v1/tasks/l2t349']
    assert task_wrap is None
