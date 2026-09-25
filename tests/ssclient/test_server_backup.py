import pytest

from ssclient import errors
from ssclient.server.backup import BackupService
from ssclient.server.server_id import ServerId
from ssclient.task_entities import TaskState
from tests.conftest import FakeRequest, task_response

SERVER_ID = ServerId('l2s99')
BACKUP_PATH = 'api/v1/servers/l2s99/backup'
POINTS_PATH = '{path}/restore-points'.format(path=BACKUP_PATH)
TASK_PATH = 'api/v1/tasks/l2t345'
TASK_WRAP = {'task_id': 'l2t345'}

SCHEDULE = {
    'hour': 3,
    'minute': 30,
    'daily': {'keep': 7, 'backup_storage_id': 5},
    'weekly': {'keep': 4, 'backup_storage_id': 5, 'weekday': 'sunday'},
    'monthly': {'keep': 2, 'backup_storage_id': 6, 'day_of_month': 'last'},
}

# Точка без полей, которые publisher не отдаёт при значении `null`.
BARE_POINT = {
    'id': 40,
    'server_id': 'l2s99',
    'size_mb': 0,
    'state': 'in_progress',
    'retained_by': [],
    'is_manual': False,
}


def _point(point_id: int, state: str, *, is_manual: bool = True):
    return dict(BARE_POINT, id=point_id, state=state, is_manual=is_manual, name='manual')


def _service(fake_http_client) -> BackupService:
    return BackupService(fake_http_client, SERVER_ID)


async def test_storages_reads_the_storefront_of_the_server(fake_http_client):
    storefront = {'storages': [{'id': 5, 'sort_order': 1, 'price_per_gb': 1.5}], 'limits': {}}
    fake_http_client.on('GET', '{path}/storages'.format(path=BACKUP_PATH), storefront)

    assert await _service(fake_http_client).storages() == storefront


async def test_get_of_server_without_backup_has_no_schedule(fake_http_client):
    fake_http_client.on('GET', BACKUP_PATH, {'enabled': False})

    backup = await _service(fake_http_client).get()

    assert backup == {'enabled': False}
    assert 'schedule' not in backup


async def test_enable_posts_the_schedule_and_returns_the_task_without_wait(fake_http_client):
    fake_http_client.on('POST', BACKUP_PATH, TASK_WRAP)

    task_wrap = await _service(fake_http_client).enable(SCHEDULE)

    assert fake_http_client.requests == [FakeRequest('POST', BACKUP_PATH, SCHEDULE)]
    assert task_wrap == TASK_WRAP


async def test_enable_with_wait_polls_the_task_and_reads_the_backup(fake_http_client):
    fake_http_client.on('POST', BACKUP_PATH, TASK_WRAP)
    fake_http_client.on('GET', TASK_PATH, task_response('l2t345', TaskState.completed))
    fake_http_client.on('GET', BACKUP_PATH, {'enabled': True, 'schedule': SCHEDULE})

    backup = await _service(fake_http_client).enable(SCHEDULE, wait=True)

    assert fake_http_client.paths('GET') == [TASK_PATH, BACKUP_PATH]
    assert backup == {'enabled': True, 'schedule': SCHEDULE}


async def test_update_puts_the_whole_schedule(fake_http_client):
    fake_http_client.on('PUT', BACKUP_PATH, TASK_WRAP)

    task_wrap = await _service(fake_http_client).update(SCHEDULE)

    assert fake_http_client.requests == [FakeRequest('PUT', BACKUP_PATH, SCHEDULE)]
    assert task_wrap == TASK_WRAP


async def test_update_with_wait_on_already_completed_task_does_not_poll(fake_http_client):
    fake_http_client.on('PUT', BACKUP_PATH, {'task_id': 'already_completed_task'})
    fake_http_client.on('GET', BACKUP_PATH, {'enabled': True, 'schedule': SCHEDULE})

    await _service(fake_http_client).update(SCHEDULE, wait=True)

    assert fake_http_client.paths('GET') == [BACKUP_PATH]


async def test_disable_deletes_without_return_task_and_polls_the_task(fake_http_client):
    fake_http_client.on('DELETE', BACKUP_PATH, TASK_WRAP)
    fake_http_client.on('GET', TASK_PATH, task_response('l2t345', TaskState.completed))

    task_wrap = await _service(fake_http_client).disable(wait=True)

    assert fake_http_client.paths('DELETE') == [BACKUP_PATH]
    assert fake_http_client.paths('GET') == [TASK_PATH]
    assert task_wrap is None


async def test_list_restore_points_tolerates_absent_fields(fake_http_client):
    fake_http_client.on('GET', POINTS_PATH, {'restore_points': [BARE_POINT]})

    restore_points = await _service(fake_http_client).list_restore_points()

    assert restore_points == [BARE_POINT]


@pytest.mark.parametrize(('name', 'expected_payload'), [
    (None, {}),
    ('before-upgrade', {'name': 'before-upgrade'}),
])
async def test_create_restore_point_without_wait_returns_the_task(fake_http_client, name, expected_payload):
    fake_http_client.on('POST', POINTS_PATH, TASK_WRAP)

    task_wrap = await _service(fake_http_client).create_restore_point(name=name)

    assert fake_http_client.requests == [FakeRequest('POST', POINTS_PATH, expected_payload)]
    assert task_wrap == TASK_WRAP


async def test_create_restore_point_with_wait_returns_the_new_manual_point(fake_http_client):
    old_manual = _point(10, 'active')
    scheduled = _point(12, 'active', is_manual=False)
    taken = _point(11, 'active')
    fake_http_client.on(
        'GET', POINTS_PATH,
        {'restore_points': [old_manual]},
        {'restore_points': [old_manual, taken, scheduled]},
    )
    fake_http_client.on('POST', POINTS_PATH, TASK_WRAP)
    fake_http_client.on('GET', TASK_PATH, task_response('l2t345', TaskState.completed))

    restore_point = await _service(fake_http_client).create_restore_point(wait=True)

    assert restore_point == taken
    assert fake_http_client.paths('GET') == [POINTS_PATH, TASK_PATH, POINTS_PATH]


async def test_create_restore_point_with_wait_fails_on_failed_point(fake_http_client):
    fake_http_client.on(
        'GET', POINTS_PATH,
        {'restore_points': []},
        {'restore_points': [_point(11, 'failed')]},
    )
    fake_http_client.on('POST', POINTS_PATH, TASK_WRAP)
    fake_http_client.on('GET', TASK_PATH, task_response('l2t345', TaskState.completed))

    with pytest.raises(errors.RestorePointFailedError) as exc_info:
        await _service(fake_http_client).create_restore_point(wait=True)

    assert (exc_info.value.restore_point_id, exc_info.value.task_id) == (11, 'l2t345')


async def test_create_restore_point_with_wait_fails_without_new_manual_point(fake_http_client):
    fake_http_client.on(
        'GET', POINTS_PATH,
        {'restore_points': [_point(10, 'active')]},
        {'restore_points': [_point(10, 'active'), _point(12, 'active', is_manual=False)]},
    )
    fake_http_client.on('POST', POINTS_PATH, TASK_WRAP)
    fake_http_client.on('GET', TASK_PATH, task_response('l2t345', TaskState.completed))

    with pytest.raises(errors.RestorePointMissingError):
        await _service(fake_http_client).create_restore_point(wait=True)


async def test_restore_posts_empty_body_and_polls_the_task(fake_http_client):
    restore_path = '{path}/31/restore'.format(path=POINTS_PATH)
    fake_http_client.on('POST', restore_path, TASK_WRAP)
    fake_http_client.on('GET', TASK_PATH, task_response('l2t345', TaskState.completed))

    task_wrap = await _service(fake_http_client).restore(31, wait=True)

    assert fake_http_client.requests[0] == FakeRequest('POST', restore_path, {})
    assert fake_http_client.paths('GET') == [TASK_PATH]
    assert task_wrap is None


@pytest.mark.parametrize(('location_id', 'expected_payload'), [
    (None, {}),
    ('ds2', {'location_id': 'ds2'}),
])
async def test_restore_nearby_sends_the_target_location_only_when_given(
    fake_http_client, location_id, expected_payload,
):
    nearby_path = '{path}/31/restore-nearby'.format(path=POINTS_PATH)
    fake_http_client.on('POST', nearby_path, TASK_WRAP)

    task_wrap = await _service(fake_http_client).restore_nearby(31, location_id=location_id)

    assert fake_http_client.requests == [FakeRequest('POST', nearby_path, expected_payload)]
    assert task_wrap == TASK_WRAP


async def test_delete_restore_point_asks_the_publisher_for_the_reference_to_the_task(fake_http_client):
    expected_path = '{path}/31?return_task=true'.format(path=POINTS_PATH)
    fake_http_client.on('DELETE', expected_path, TASK_WRAP)
    fake_http_client.on('GET', TASK_PATH, task_response('l2t345', TaskState.completed))

    task_wrap = await _service(fake_http_client).delete_restore_point(31, wait=True)

    assert fake_http_client.paths('DELETE') == [expected_path]
    assert fake_http_client.paths('GET') == [TASK_PATH]
    assert task_wrap is None
