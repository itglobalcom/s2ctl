import pytest

from ssclient.task_entities import TaskState
from ssclient.vmware.nic import VmwareServerNicService
from tests.conftest import FakeRequest, task_response
from tests.ssclient.vmware.conftest import (
    NIC_ID,
    NIC_PATH,
    NICS_PATH,
    SERVER_ID,
    SHARED_NICS_PATH,
)

# Состав полей интерфейса не проверяется: истина — DTO publisher'а, не клиент.
NIC_ENTITY = {'id': NIC_ID, 'number': 0}
OTHER_NIC_ENTITY = {'id': 4, 'number': 1}

CONNECT_CLIENT_KWARGS = {'network_id': 42, 'ip': '10.0.0.5'}
CONNECT_SHARED_KWARGS = {'bandwidth_mbps': 100}
UPDATE_KWARGS = {'network_id': 42, 'bandwidth_mbps': 200, 'ip': '10.0.0.6'}

# Подключение к клиентской сети и к общей — две операции контракта с разными маршрутами
# и разной формой запроса (сеть с адресом против полосы), а не одна операция с признаком
# общей сети. Отключение отдаёт ссылку на задачу само, без `return_task=true`.
NIC_ROUTE_CASES = (
    (
        'list',
        (),
        {},
        FakeRequest('GET', NICS_PATH),
        {'nics': [NIC_ENTITY]},
        [NIC_ENTITY],
    ),
    (
        'connect_client_network',
        (),
        CONNECT_CLIENT_KWARGS,
        FakeRequest('POST', NICS_PATH, {
            'network_id': 42,
            'ip': '10.0.0.5',
            'force_customization': False,
        }),
        {'task_id': 'vmw81'},
        {'task_id': 'vmw81'},
    ),
    (
        'connect_shared_network',
        (),
        CONNECT_SHARED_KWARGS,
        FakeRequest('POST', SHARED_NICS_PATH, {
            'bandwidth_mbps': 100,
            'force_customization': False,
        }),
        {'task_id': 'vmw82'},
        {'task_id': 'vmw82'},
    ),
    (
        'update',
        (NIC_ID,),
        UPDATE_KWARGS,
        FakeRequest('PUT', NIC_PATH, {
            'network_id': 42,
            'bandwidth_mbps': 200,
            'ip': '10.0.0.6',
            'force_customization': False,
        }),
        {'task_id': 'vmw83'},
        {'task_id': 'vmw83'},
    ),
    (
        'disconnect',
        (NIC_ID,),
        {},
        FakeRequest('DELETE', NIC_PATH),
        {'task_id': 'vmw84'},
        {'task_id': 'vmw84'},
    ),
)

# Ожидание любой правки интерфейсов отдаёт набор: у созданного интерфейса id взять
# неоткуда, а чтения одного интерфейса контракт вообще не предлагает.
NIC_SET_AFTER_WAIT_CASES = (
    ('connect_client_network', (), CONNECT_CLIENT_KWARGS, 'POST', NICS_PATH),
    ('connect_shared_network', (), CONNECT_SHARED_KWARGS, 'POST', SHARED_NICS_PATH),
    ('update', (NIC_ID,), UPDATE_KWARGS, 'PUT', NIC_PATH),
)


def _service(fake_http_client) -> VmwareServerNicService:
    return VmwareServerNicService(fake_http_client, SERVER_ID)


@pytest.mark.parametrize(
    'method_name,call_args,call_kwargs,expected_request,response,expected_result',
    NIC_ROUTE_CASES,
)
async def test_each_nic_operation_addresses_its_own_route(
    fake_http_client, method_name, call_args, call_kwargs, expected_request, response,
    expected_result,
):
    fake_http_client.on(expected_request.method, expected_request.path, response)

    operation = getattr(_service(fake_http_client), method_name)
    operation_resp = await operation(*call_args, **call_kwargs)

    assert fake_http_client.requests == [expected_request]
    assert operation_resp == expected_result


@pytest.mark.parametrize(
    'method_name,call_args,call_kwargs,operation_method,operation_path',
    NIC_SET_AFTER_WAIT_CASES,
)
async def test_nic_operation_with_wait_returns_the_whole_set_of_nics(
    fake_http_client, method_name, call_args, call_kwargs, operation_method, operation_path,
):
    fake_http_client.on(operation_method, operation_path, {'task_id': 'vmw85'})
    # Ресурсы задачи VMware — только server и network: id интерфейса там не публикуется,
    # и попытка прочитать интерфейс по нему ушла бы в незаданный маршрут.
    fake_http_client.on('GET', 'api/v1/tasks/vmw85', task_response(
        'vmw85', TaskState.completed, (('server', str(SERVER_ID)), ('network', '42')),
    ))
    fake_http_client.on('GET', NICS_PATH, {'nics': [NIC_ENTITY, OTHER_NIC_ENTITY]})

    operation = getattr(_service(fake_http_client), method_name)
    nics = await operation(*call_args, wait=True, **call_kwargs)

    assert fake_http_client.paths('GET') == ['api/v1/tasks/vmw85', NICS_PATH]
    assert nics == [NIC_ENTITY, OTHER_NIC_ENTITY]


async def test_disconnect_with_wait_polls_task_and_returns_nothing(fake_http_client):
    fake_http_client.on('DELETE', NIC_PATH, {'task_id': 'vmw86'})
    fake_http_client.on('GET', 'api/v1/tasks/vmw86', task_response('vmw86', TaskState.completed))

    disconnect_resp = await _service(fake_http_client).disconnect(NIC_ID, wait=True)

    # Отключённый интерфейс нечего перечитывать: после ожидания печатать нечего.
    assert fake_http_client.paths('GET') == ['api/v1/tasks/vmw86']
    assert disconnect_resp is None
