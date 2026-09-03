import pytest

from ssclient.task_entities import TaskState
from ssclient.vmware.server import VmwareServerService
from ssclient.vmware.server_entities import VmwareServerGpu, VmwareServerOrder
from tests.conftest import FakeRequest, task_response
from tests.ssclient.vmware.conftest import SERVER_ID, SERVER_PATH, SERVERS_PATH

NEW_SERVER_ID = 777
NEW_SERVER_PATH = '{path}/{server_id}'.format(path=SERVERS_PATH, server_id=NEW_SERVER_ID)

VERIFY_PATH = '{path}/verify'.format(path=SERVERS_PATH)
NAME_PATH = '{path}/name'.format(path=SERVER_PATH)
COMPUTER_NAME_PATH = '{path}/computer-name'.format(path=SERVER_PATH)
FIREWALL_PATH = '{path}/firewall'.format(path=SERVER_PATH)
NESTED_HYPERVISOR_PATH = '{path}/nested-hypervisor'.format(path=SERVER_PATH)

# Состав полей ответа сервера не проверяется: истина — DTO publisher'а, не клиент.
SERVER_ENTITY = {'id': SERVER_ID, 'name': 'srv'}
NEW_SERVER_ENTITY = {'id': NEW_SERVER_ID, 'name': 'srv-copy'}

FIREWALL_RULE = {
    'name': 'ssh',
    'traffic_direction': 'Inbound',
    'action': 'Allow',
    'protocol': 'Tcp',
    'source': '0.0.0.0/0',
    'source_port': 'any',
    'destination': '10.0.0.5',
    'destination_port': '22',
}

ORDER = VmwareServerOrder(
    location_id=1,
    name='srv',
    image_id=5,
    cpu_count=2,
    ram_mb=4096,
    system_disk_size_mb=51200,
    ssh_keys=(7,),
    gpu=VmwareServerGpu(gpu_model_id=3, vram_mb=8192, card_count=1),
)

ORDER_PAYLOAD = {
    'location_id': 1,
    'name': 'srv',
    'image_id': 5,
    'cpu_count': 2,
    'ram_mb': 4096,
    'system_disk_size_mb': 51200,
    'computer_name': None,
    'system_disk_type': None,
    'public_network_id': None,
    'network_bandwidth_mbps': None,
    'backup_enabled': False,
    'backup_period': None,
    # Ключи уезжают списком: кортеж заказа не сериализуется в JSON-массив сам собой.
    'ssh_keys': [7],
    'need_sysprep': False,
    'nested_hypervisor': False,
    # Нарезку GPU platform выбирает по всей тройке сразу, поэтому она едет одним объектом.
    'gpu': {'gpu_model_id': 3, 'vram_mb': 8192, 'card_count': 1},
}

# Копия и переустановка заказывают новую машину: id в ответе заказа — её, а не исходной.
NEW_SERVER_ORDER_CASES = (
    (
        'copy',
        {'name': 'srv-copy', 'client_network_id': 42},
        '{path}/copy'.format(path=SERVER_PATH),
        {'name': 'srv-copy', 'client_network_id': 42},
    ),
    (
        'rebuild',
        {'image_id': 9, 'need_sysprep': True},
        '{path}/rebuild'.format(path=SERVER_PATH),
        {'image_id': 9, 'need_sysprep': True},
    ),
)

NESTED_HYPERVISOR_CASES = (
    ('enable_nested_hypervisor', '{path}/enable'.format(path=NESTED_HYPERVISOR_PATH)),
    ('disable_nested_hypervisor', '{path}/disable'.format(path=NESTED_HYPERVISOR_PATH)),
)


def _service(fake_http_client) -> VmwareServerService:
    return VmwareServerService(fake_http_client)


@pytest.mark.parametrize('location_id,expected_path', (
    (None, SERVERS_PATH),
    (1, '{path}?location_id=1'.format(path=SERVERS_PATH)),
))
async def test_list_unwraps_servers_and_sends_only_given_filter(
    fake_http_client, location_id, expected_path,
):
    fake_http_client.on('GET', expected_path, {'servers': [SERVER_ENTITY]})

    servers = await _service(fake_http_client).list(location_id=location_id)

    assert fake_http_client.paths('GET') == [expected_path]
    assert servers == [SERVER_ENTITY]


async def test_get_reads_server_by_id(fake_http_client):
    fake_http_client.on('GET', SERVER_PATH, {'server': SERVER_ENTITY})

    server = await _service(fake_http_client).get(SERVER_ID)

    assert fake_http_client.paths('GET') == [SERVER_PATH]
    assert server == SERVER_ENTITY


async def test_create_posts_whole_order_and_returns_id_of_ordered_server(fake_http_client):
    fake_http_client.on('POST', SERVERS_PATH, {'server_id': NEW_SERVER_ID, 'task_id': 'vmw11'})

    order_ref = await _service(fake_http_client).create(ORDER)

    assert fake_http_client.requests == [FakeRequest('POST', SERVERS_PATH, ORDER_PAYLOAD)]
    assert order_ref == {'server_id': NEW_SERVER_ID, 'task_id': 'vmw11'}


async def test_create_with_wait_reads_server_by_id_from_order_response(fake_http_client):
    fake_http_client.on('POST', SERVERS_PATH, {'server_id': NEW_SERVER_ID, 'task_id': 'vmw11'})
    # Ресурсы задачи ведут в другое место — заказ отдаёт id сервера сам, и берётся он оттуда.
    fake_http_client.on(
        'GET',
        'api/v1/tasks/vmw11',
        task_response('vmw11', TaskState.completed, (('vmware_server', str(SERVER_ID)),)),
    )
    fake_http_client.on('GET', NEW_SERVER_PATH, {'server': NEW_SERVER_ENTITY})

    server = await _service(fake_http_client).create(ORDER, wait=True)

    assert fake_http_client.paths('GET') == ['api/v1/tasks/vmw11', NEW_SERVER_PATH]
    assert server == NEW_SERVER_ENTITY


async def test_verify_posts_the_same_order_to_own_route_and_orders_nothing(fake_http_client):
    fake_http_client.on('POST', VERIFY_PATH, None)

    verify_resp = await _service(fake_http_client).verify(ORDER)

    # Тело предпроверки совпадает с телом создания — иначе проверяется не тот заказ.
    assert fake_http_client.requests == [FakeRequest('POST', VERIFY_PATH, ORDER_PAYLOAD)]
    assert verify_resp is None


async def test_set_configuration_always_returns_task(fake_http_client):
    fake_http_client.on('PUT', SERVER_PATH, {'task_id': 'vmw12'})

    task_wrap = await _service(fake_http_client).set_configuration(
        SERVER_ID, cpu=4, ram_mb=8192, system_disk_size_mb=102400,
    )

    # Смена конфигурации всегда заводит задачу: ветки «ответ без задачи» у этого маршрута нет.
    assert fake_http_client.requests == [FakeRequest('PUT', SERVER_PATH, {
        'cpu': 4,
        'ram_mb': 8192,
        'system_disk_size_mb': 102400,
    })]
    assert task_wrap == {'task_id': 'vmw12'}


async def test_rename_puts_name_and_leaves_no_task_to_wait_for(fake_http_client):
    fake_http_client.on('PUT', NAME_PATH, None)

    rename_resp = await _service(fake_http_client).rename(SERVER_ID, name='srv-renamed')

    # Переименование применяется синхронно: publisher отдаёт пустое тело, задачи нет,
    # поэтому ни опроса, ни перечитывания сервера быть не должно.
    assert fake_http_client.requests == [FakeRequest('PUT', NAME_PATH, {'name': 'srv-renamed'})]
    assert rename_resp is None


async def test_set_computer_name_puts_own_subresource(fake_http_client):
    fake_http_client.on('PUT', COMPUTER_NAME_PATH, {'task_id': 'vmw13'})

    task_wrap = await _service(fake_http_client).set_computer_name(
        SERVER_ID, computer_name='srv-host', force_customization=True,
    )

    # Hostname гостевой ОС — не отображаемое имя: свой маршрут и своя задача.
    assert fake_http_client.requests == [FakeRequest('PUT', COMPUTER_NAME_PATH, {
        'computer_name': 'srv-host',
        'force_customization': True,
    })]
    assert task_wrap == {'task_id': 'vmw13'}


@pytest.mark.parametrize(
    'method_name,call_kwargs,expected_path,expected_payload', NEW_SERVER_ORDER_CASES,
)
async def test_order_of_new_server_with_wait_reads_it_by_id_from_order_response(
    fake_http_client, method_name, call_kwargs, expected_path, expected_payload,
):
    fake_http_client.on('POST', expected_path, {'server_id': NEW_SERVER_ID, 'task_id': 'vmw14'})
    # Ресурсы задачи называют исходную машину — читать нужно новую, из ответа заказа.
    fake_http_client.on(
        'GET',
        'api/v1/tasks/vmw14',
        task_response('vmw14', TaskState.completed, (('vmware_server', str(SERVER_ID)),)),
    )
    fake_http_client.on('GET', NEW_SERVER_PATH, {'server': NEW_SERVER_ENTITY})

    order = getattr(_service(fake_http_client), method_name)
    server = await order(SERVER_ID, wait=True, **call_kwargs)

    assert fake_http_client.requests[0] == FakeRequest('POST', expected_path, expected_payload)
    assert fake_http_client.paths('GET') == ['api/v1/tasks/vmw14', NEW_SERVER_PATH]
    assert server == NEW_SERVER_ENTITY


async def test_delete_gets_task_without_return_task_query(fake_http_client):
    fake_http_client.on('DELETE', SERVER_PATH, {'task_id': 'vmw15'})

    task_wrap = await _service(fake_http_client).delete(SERVER_ID)

    # VMware-сервер отдаёт ссылку на задачу сам: `return_task=true` из vStack здесь лишний.
    assert fake_http_client.requests == [FakeRequest('DELETE', SERVER_PATH)]
    assert task_wrap == {'task_id': 'vmw15'}


@pytest.mark.parametrize('method_name,expected_path', NESTED_HYPERVISOR_CASES)
async def test_nested_hypervisor_switch_posts_to_own_route(
    fake_http_client, method_name, expected_path,
):
    fake_http_client.on('POST', expected_path, {'task_id': 'vmw16'})

    switch = getattr(_service(fake_http_client), method_name)
    task_ref = await switch(SERVER_ID)

    assert fake_http_client.requests == [FakeRequest('POST', expected_path, {})]
    assert task_ref == {'task_id': 'vmw16'}


@pytest.mark.parametrize('raw_task_id,expected_get_paths', (
    ('vmw16', ['api/v1/tasks/vmw16', SERVER_PATH]),
    (None, [SERVER_PATH]),
))
async def test_nested_hypervisor_with_wait_polls_task_only_when_it_exists(
    fake_http_client, raw_task_id, expected_get_paths,
):
    # Идемпотентный исход: состояние уже требуемое, задача не заводится и `task_id`
    # приходит явным null — ждать нечего, но сервер перечитать всё равно нужно.
    enable_path = '{path}/enable'.format(path=NESTED_HYPERVISOR_PATH)
    fake_http_client.on('POST', enable_path, {'task_id': raw_task_id})
    fake_http_client.on('GET', 'api/v1/tasks/vmw16', task_response('vmw16', TaskState.completed))
    fake_http_client.on('GET', SERVER_PATH, {'server': SERVER_ENTITY})

    server = await _service(fake_http_client).enable_nested_hypervisor(SERVER_ID, wait=True)

    assert fake_http_client.paths('GET') == expected_get_paths
    assert server == SERVER_ENTITY


async def test_get_firewall_unwraps_rules(fake_http_client):
    fake_http_client.on('GET', FIREWALL_PATH, {'rules': [FIREWALL_RULE]})

    rules = await _service(fake_http_client).firewall(SERVER_ID).get()

    # Экран самой машины — подресурс сервера, а не экран на границе сети (это edge).
    assert fake_http_client.paths('GET') == [FIREWALL_PATH]
    assert rules == [FIREWALL_RULE]


async def test_update_firewall_replaces_whole_rule_set(fake_http_client):
    fake_http_client.on('PUT', FIREWALL_PATH, {'task_id': 'vmw17'})

    task_wrap = await _service(fake_http_client).firewall(SERVER_ID).update(rules=[FIREWALL_RULE])

    assert fake_http_client.requests == [
        FakeRequest('PUT', FIREWALL_PATH, {'rules': [FIREWALL_RULE]}),
    ]
    assert task_wrap == {'task_id': 'vmw17'}


async def test_update_firewall_with_wait_survives_response_without_task(fake_http_client):
    # Правку без фактических изменений publisher закрывает 204 без тела: задачи нет,
    # ждать нечего — операция обязана дочитать правила, а не упасть на пустом ответе.
    fake_http_client.on('PUT', FIREWALL_PATH, None)
    fake_http_client.on('GET', FIREWALL_PATH, {'rules': [FIREWALL_RULE]})

    rules = await _service(fake_http_client).firewall(SERVER_ID).update(
        rules=[FIREWALL_RULE], wait=True,
    )

    assert fake_http_client.paths('GET') == [FIREWALL_PATH]
    assert rules == [FIREWALL_RULE]
