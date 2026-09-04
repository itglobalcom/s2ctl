import pytest

from ssclient.task_entities import TaskState
from ssclient.vmware.snapshot import VmwareServerSnapshotService
from tests.conftest import FakeRequest, task_response
from tests.ssclient.vmware.conftest import SERVER_ID, SNAPSHOT_PATH

RESTORE_PATH = '{path}/restore'.format(path=SNAPSHOT_PATH)

# Состав полей снимка не проверяется: истина — DTO publisher'а, не клиент.
SNAPSHOT_ENTITY = {'name': 'before-update', 'created': '2026-09-01T10:00:00'}

# Все четыре операции адресуют единственный снимок сервера: сегмента с id снимка
# в маршрутах нет, и появиться он не должен — снимков у VMware-сервера не бывает много.
SNAPSHOT_ROUTE_CASES = (
    (
        'get',
        {},
        FakeRequest('GET', SNAPSHOT_PATH),
        {'snapshot': SNAPSHOT_ENTITY},
        SNAPSHOT_ENTITY,
    ),
    (
        'create',
        {'name': 'before-update'},
        FakeRequest('POST', SNAPSHOT_PATH, {'name': 'before-update'}),
        {'task_id': 'vmw91'},
        {'task_id': 'vmw91'},
    ),
    (
        'restore',
        {},
        FakeRequest('POST', RESTORE_PATH, {}),
        {'task_id': 'vmw92'},
        {'task_id': 'vmw92'},
    ),
    (
        # Удаление снимка отдаёт ссылку на задачу само, без `return_task=true`.
        'delete',
        {},
        FakeRequest('DELETE', SNAPSHOT_PATH),
        {'task_id': 'vmw93'},
        {'task_id': 'vmw93'},
    ),
)

NOTHING_TO_READ_BACK_CASES = (
    ('restore', 'POST', RESTORE_PATH),
    ('delete', 'DELETE', SNAPSHOT_PATH),
)


def _service(fake_http_client) -> VmwareServerSnapshotService:
    return VmwareServerSnapshotService(fake_http_client, SERVER_ID)


@pytest.mark.parametrize(
    'method_name,call_kwargs,expected_request,response,expected_result', SNAPSHOT_ROUTE_CASES,
)
async def test_each_snapshot_operation_addresses_the_single_snapshot_of_the_server(
    fake_http_client, method_name, call_kwargs, expected_request, response, expected_result,
):
    fake_http_client.on(expected_request.method, expected_request.path, response)

    operation = getattr(_service(fake_http_client), method_name)
    operation_resp = await operation(**call_kwargs)

    assert fake_http_client.requests == [expected_request]
    assert operation_resp == expected_result


@pytest.mark.parametrize(
    'response', ({}, {'snapshot': None}), ids=('key-omitted', 'explicit-null'),
)
async def test_get_returns_nothing_for_a_server_without_snapshot(fake_http_client, response):
    # Сервер без снимка — не ошибка: publisher отвечает 200 и телом без снимка.
    # Фактическая форма такого тела — пустой объект: null-поля publisher из ответа
    # выбрасывает (`NullValueHandling.Ignore`). Форма с явным null проверяется рядом:
    # от этой настройки publisher'а разбор ответа зависеть не должен.
    # (404 остаётся исходом отсутствующего сервера, и его разбирает http-клиент.)
    fake_http_client.on('GET', SNAPSHOT_PATH, response)

    snapshot = await _service(fake_http_client).get()

    assert fake_http_client.paths('GET') == [SNAPSHOT_PATH]
    assert snapshot is None


async def test_create_with_wait_reads_the_taken_snapshot_back(fake_http_client):
    fake_http_client.on('POST', SNAPSHOT_PATH, {'task_id': 'vmw94'})
    fake_http_client.on('GET', 'api/v1/tasks/vmw94', task_response('vmw94', TaskState.completed))
    fake_http_client.on('GET', SNAPSHOT_PATH, {'snapshot': SNAPSHOT_ENTITY})

    # Снимок адресуется сервером, поэтому после ожидания он читается тем же маршрутом —
    # id из ответа операции или из ресурсов задачи для этого не нужен.
    snapshot = await _service(fake_http_client).create(name='before-update', wait=True)

    assert fake_http_client.paths('GET') == ['api/v1/tasks/vmw94', SNAPSHOT_PATH]
    assert snapshot == SNAPSHOT_ENTITY


@pytest.mark.parametrize('method_name,operation_method,operation_path', NOTHING_TO_READ_BACK_CASES)
async def test_snapshot_operation_with_wait_polls_task_and_returns_nothing(
    fake_http_client, method_name, operation_method, operation_path,
):
    fake_http_client.on(operation_method, operation_path, {'task_id': 'vmw95'})
    fake_http_client.on('GET', 'api/v1/tasks/vmw95', task_response('vmw95', TaskState.completed))

    # Откат меняет сам сервер, а не снимок, удалённый снимок читать неоткуда:
    # после ожидания обе операции печатать нечего.
    operation = getattr(_service(fake_http_client), method_name)
    operation_resp = await operation(wait=True)

    assert fake_http_client.paths('GET') == ['api/v1/tasks/vmw95']
    assert operation_resp is None
