import pytest

from ssclient.task_entities import TaskState
from ssclient.vmware.volume import VmwareServerVolumeService
from tests.conftest import FakeRequest, task_response
from tests.ssclient.vmware.conftest import (
    SERVER_ID,
    VOLUME_ID,
    VOLUME_PATH,
    VOLUMES_PATH,
)

# Состав полей диска не проверяется: истина — DTO publisher'а, не клиент.
VOLUME_ENTITY = {'id': VOLUME_ID, 'name': 'data'}
OTHER_VOLUME_ENTITY = {'id': 8, 'name': 'logs'}

CREATE_KWARGS = {'name': 'data', 'disk_type': 'ssd', 'size_mb': 10240}

# Пять операций дисков — пять маршрутов publisher'а. Удаление отдаёт ссылку на задачу
# само: `return_task=true` из раздела vStack здесь не нужен, и его в пути быть не должно.
VOLUME_ROUTE_CASES = (
    (
        'list',
        (),
        {},
        FakeRequest('GET', VOLUMES_PATH),
        {'volumes': [VOLUME_ENTITY]},
        [VOLUME_ENTITY],
    ),
    (
        'get',
        (VOLUME_ID,),
        {},
        FakeRequest('GET', VOLUME_PATH),
        {'volume': VOLUME_ENTITY},
        VOLUME_ENTITY,
    ),
    (
        'create',
        (),
        CREATE_KWARGS,
        FakeRequest('POST', VOLUMES_PATH, CREATE_KWARGS),
        {'task_id': 'vmw71'},
        {'task_id': 'vmw71'},
    ),
    (
        'edit',
        (VOLUME_ID,),
        {'size_mb': 20480},
        # Имя не передано — в теле явный null, и publisher оставляет диску текущее имя.
        FakeRequest('PUT', VOLUME_PATH, {'name': None, 'size_mb': 20480}),
        {'task_id': 'vmw72'},
        {'task_id': 'vmw72'},
    ),
    (
        'delete',
        (VOLUME_ID,),
        {},
        FakeRequest('DELETE', VOLUME_PATH),
        {'task_id': 'vmw73'},
        {'task_id': 'vmw73'},
    ),
)


def _service(fake_http_client) -> VmwareServerVolumeService:
    return VmwareServerVolumeService(fake_http_client, SERVER_ID)


@pytest.mark.parametrize(
    'method_name,call_args,call_kwargs,expected_request,response,expected_result',
    VOLUME_ROUTE_CASES,
)
async def test_each_volume_operation_addresses_its_own_route(
    fake_http_client, method_name, call_args, call_kwargs, expected_request, response,
    expected_result,
):
    fake_http_client.on(expected_request.method, expected_request.path, response)

    operation = getattr(_service(fake_http_client), method_name)
    operation_resp = await operation(*call_args, **call_kwargs)

    assert fake_http_client.requests == [expected_request]
    assert operation_resp == expected_result


async def test_create_with_wait_returns_the_whole_set_of_volumes(fake_http_client):
    fake_http_client.on('POST', VOLUMES_PATH, {'task_id': 'vmw74'})
    # Задача VMware публикует ресурсы только двух типов, server и network: id созданного
    # диска взять неоткуда, поэтому ожидание отдаёт набор дисков сервера, а не один диск.
    # Попытка прочитать диск по id из ресурсов задачи пошла бы в незаданный маршрут.
    fake_http_client.on('GET', 'api/v1/tasks/vmw74', task_response(
        'vmw74', TaskState.completed, (('server', str(SERVER_ID)), ('network', '42')),
    ))
    fake_http_client.on('GET', VOLUMES_PATH, {'volumes': [VOLUME_ENTITY, OTHER_VOLUME_ENTITY]})

    volumes = await _service(fake_http_client).create(wait=True, **CREATE_KWARGS)

    assert fake_http_client.paths('GET') == ['api/v1/tasks/vmw74', VOLUMES_PATH]
    assert volumes == [VOLUME_ENTITY, OTHER_VOLUME_ENTITY]


async def test_edit_with_wait_reads_the_edited_volume_by_id_from_the_argument(fake_http_client):
    fake_http_client.on('PUT', VOLUME_PATH, {'task_id': 'vmw75'})
    fake_http_client.on('GET', 'api/v1/tasks/vmw75', task_response('vmw75', TaskState.completed))
    fake_http_client.on('GET', VOLUME_PATH, {'volume': VOLUME_ENTITY})

    # Правка адресует существующий диск — id известен из аргумента, и возвращается
    # сам диск, а не весь набор.
    volume = await _service(fake_http_client).edit(VOLUME_ID, size_mb=20480, wait=True)

    assert fake_http_client.paths('GET') == ['api/v1/tasks/vmw75', VOLUME_PATH]
    assert volume == VOLUME_ENTITY


async def test_delete_with_wait_polls_task_and_returns_nothing(fake_http_client):
    fake_http_client.on('DELETE', VOLUME_PATH, {'task_id': 'vmw76'})
    fake_http_client.on('GET', 'api/v1/tasks/vmw76', task_response('vmw76', TaskState.completed))

    delete_resp = await _service(fake_http_client).delete(VOLUME_ID, wait=True)

    # Удалённый диск нечего перечитывать: после ожидания печатать нечего.
    assert fake_http_client.paths('GET') == ['api/v1/tasks/vmw76']
    assert delete_resp is None
