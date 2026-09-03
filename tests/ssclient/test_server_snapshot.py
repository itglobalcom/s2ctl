"""Снимки vStack-сервера: `--wait` дожидается задачи и печатать после неё нечего.

Регресс на миграцию ожидания задачи: id снимка контракт в задаче не публикует,
поэтому исход ожидания — пустой ответ, а не чтение ресурса.
"""
from ssclient.server.snapshot import SnapshotService
from ssclient.task_entities import TaskState
from tests.conftest import FakeRequest, task_response

SNAPSHOTS_PATH = 'api/v1/servers/l2s99/snapshots'
ROLLBACK_PATH = '{path}/31/rollback'.format(path=SNAPSHOTS_PATH)


async def test_create_with_wait_polls_the_task_of_the_snapshot(fake_http_client):
    fake_http_client.on('POST', SNAPSHOTS_PATH, {'task_id': 'l2t345'})
    fake_http_client.on('GET', 'api/v1/tasks/l2t345', task_response('l2t345', TaskState.completed))

    task_wrap = await SnapshotService(fake_http_client, 'l2s99').create(name='before', wait=True)

    assert fake_http_client.requests[0] == FakeRequest(
        'POST', SNAPSHOTS_PATH, {'name': 'before'},
    )
    assert fake_http_client.paths('GET') == ['api/v1/tasks/l2t345']
    assert task_wrap is None


async def test_rollback_with_wait_polls_the_task_of_the_rollback(fake_http_client):
    fake_http_client.on('POST', ROLLBACK_PATH, {'task_id': 'l2t346'})
    fake_http_client.on('GET', 'api/v1/tasks/l2t346', task_response('l2t346', TaskState.completed))

    task_wrap = await SnapshotService(fake_http_client, 'l2s99').rollback(31, wait=True)

    assert fake_http_client.requests[0] == FakeRequest('POST', ROLLBACK_PATH, {})
    assert fake_http_client.paths('GET') == ['api/v1/tasks/l2t346']
    assert task_wrap is None


async def test_create_without_wait_returns_the_task(fake_http_client):
    fake_http_client.on('POST', SNAPSHOTS_PATH, {'task_id': 'l2t345'})

    task_wrap = await SnapshotService(fake_http_client, 'l2s99').create(name='before')

    assert task_wrap == {'task_id': 'l2t345'}
