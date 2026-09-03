import pytest

from ssclient.task_entities import TaskState
from ssclient.vmware.network import VmwareNetworkService, VmwareServerNic
from tests.conftest import FakeRequest, task_response
from tests.ssclient.vmware.conftest import (
    EDIT_NETWORK_REQUIRED_FIELDS,
    NETWORK_ENTITY,
    NETWORK_ID,
    NETWORK_PATH,
    NETWORKS_PATH,
)

SERVERS_PATH = '{network_path}/servers'.format(network_path=NETWORK_PATH)

# Три типа сети — три маршрута создания с разной формой запроса, а не один маршрут
# с признаком типа: у publisher'а это три отдельные операции.
CREATE_CASES = (
    (
        'create_isolated',
        {'location_id': 1, 'name': 'net', 'address': '10.0.0.0', 'mask': 24, 'enable_dhcp': True},
        '{path}/isolated'.format(path=NETWORKS_PATH),
        {
            'location_id': 1,
            'name': 'net',
            'address': '10.0.0.0',
            'mask': 24,
            'enable_dhcp': True,
        },
    ),
    (
        'create_routed',
        {'location_id': 1, 'name': 'net', 'address': '10.0.0.0', 'mask': 24, 'bandwidth_mbps': 100},
        '{path}/routed'.format(path=NETWORKS_PATH),
        {
            'location_id': 1,
            'name': 'net',
            'address': '10.0.0.0',
            'mask': 24,
            'enable_dhcp': False,
            'bandwidth_mbps': 100,
        },
    ),
    (
        'create_public',
        {'location_id': 1, 'name': 'net', 'capacity': 'Network26'},
        '{path}/public'.format(path=NETWORKS_PATH),
        # Размер блока адресов — имя члена enum контракта (длина префикса сети),
        # а не число 26: справочник Go SDK описывает это поле неверно.
        {'location_id': 1, 'name': 'net', 'capacity': 'Network26', 'bandwidth_mbps': None},
    ),
)


@pytest.mark.parametrize('location_id,network_type,expected_path', (
    (None, None, NETWORKS_PATH),
    (1, None, '{path}?location_id=1'.format(path=NETWORKS_PATH)),
    (None, 'routed_client', '{path}?type=routed_client'.format(path=NETWORKS_PATH)),
))
async def test_list_unwraps_networks_and_sends_only_given_filters(
    fake_http_client, location_id, network_type, expected_path,
):
    fake_http_client.on('GET', expected_path, {'networks': [NETWORK_ENTITY]})

    networks = await VmwareNetworkService(fake_http_client).list(
        location_id=location_id, network_type=network_type,
    )

    assert fake_http_client.paths('GET') == [expected_path]
    assert networks == [NETWORK_ENTITY]


async def test_get_reads_network_by_id(fake_http_client):
    fake_http_client.on('GET', NETWORK_PATH, {'network': NETWORK_ENTITY})

    network = await VmwareNetworkService(fake_http_client).get(NETWORK_ID)

    assert fake_http_client.paths('GET') == [NETWORK_PATH]
    assert network == NETWORK_ENTITY


@pytest.mark.parametrize('method_name,kwargs,expected_path,expected_payload', CREATE_CASES)
async def test_create_posts_own_route_of_network_type(
    fake_http_client, method_name, kwargs, expected_path, expected_payload,
):
    fake_http_client.on('POST', expected_path, {'task_id': 'vmw901'})

    create = getattr(VmwareNetworkService(fake_http_client), method_name)
    task_wrap = await create(**kwargs)

    assert fake_http_client.requests == [FakeRequest('POST', expected_path, expected_payload)]
    assert task_wrap == {'task_id': 'vmw901'}


async def test_create_with_wait_reads_network_addressed_by_task_resources(fake_http_client):
    isolated_path = '{path}/isolated'.format(path=NETWORKS_PATH)
    fake_http_client.on('POST', isolated_path, {'task_id': 'vmw901'})
    fake_http_client.on(
        'GET', 'api/v1/tasks/vmw901',
        task_response('vmw901', TaskState.completed, resources=[
            ('server', '17'), ('network', str(NETWORK_ID)),
        ]),
    )
    fake_http_client.on('GET', NETWORK_PATH, {'network': NETWORK_ENTITY})

    network = await VmwareNetworkService(fake_http_client).create_isolated(
        location_id=1, name='net', address='10.0.0.0', wait=True,
    )

    # У VMware-задачи нет полей вида `network_id`: id созданной сети известен только
    # из resources[], причём по типу записи, а не по её порядку.
    assert fake_http_client.paths('GET') == ['api/v1/tasks/vmw901', NETWORK_PATH]
    assert network == NETWORK_ENTITY


async def test_rename_sends_name_alone_because_bandwidth_is_optional_in_contract(
    fake_http_client,
):
    fake_http_client.on('PUT', NETWORK_PATH, {'task_id': 'vmw902'})

    task_wrap = await VmwareNetworkService(fake_http_client).rename(NETWORK_ID, name='renamed')

    # Опущенная `bandwidth_mbps` в запросе правки означает «оставить как есть»,
    # поэтому смена имени обходится без чтения сети.
    assert fake_http_client.requests == [FakeRequest('PUT', NETWORK_PATH, {'name': 'renamed'})]
    assert task_wrap == {'task_id': 'vmw902'}


async def test_set_bandwidth_carries_required_name_of_current_network(fake_http_client):
    fake_http_client.on('GET', NETWORK_PATH, {'network': NETWORK_ENTITY})
    fake_http_client.on('PUT', NETWORK_PATH, {'task_id': 'vmw902'})

    task_wrap = await VmwareNetworkService(fake_http_client).set_bandwidth(
        NETWORK_ID, bandwidth_mbps=200,
    )

    edit_request = fake_http_client.requests[-1]
    # Тело правки сети обязано нести каждое обязательное поле запроса контракта,
    # иначе publisher отвечает 400 и полосу сменить нельзя.
    assert EDIT_NETWORK_REQUIRED_FIELDS <= set(edit_request.payload)
    # Обязательное имя команда не спрашивает у пользователя и не выдумывает —
    # берёт текущее из прочитанной сети.
    assert edit_request == FakeRequest('PUT', NETWORK_PATH, {
        'name': NETWORK_ENTITY['name'],
        'bandwidth_mbps': 200,
    })
    assert task_wrap == {'task_id': 'vmw902'}


async def test_edit_with_wait_survives_response_without_task(fake_http_client):
    # Правку, применённую синхронно, publisher закрывает 204 без тела: задачи нет,
    # ждать нечего — операция обязана дочитать сеть, а не упасть.
    fake_http_client.on('PUT', NETWORK_PATH, None)
    fake_http_client.on('GET', NETWORK_PATH, {'network': NETWORK_ENTITY})

    network = await VmwareNetworkService(fake_http_client).rename(
        NETWORK_ID, name='renamed', wait=True,
    )

    assert fake_http_client.paths('GET') == [NETWORK_PATH]
    assert network == NETWORK_ENTITY


async def test_delete_sends_bare_delete_and_returns_task(fake_http_client):
    fake_http_client.on('DELETE', NETWORK_PATH, {'task_id': 'vmw903'})

    task_wrap = await VmwareNetworkService(fake_http_client).delete(NETWORK_ID)

    assert fake_http_client.requests == [FakeRequest('DELETE', NETWORK_PATH)]
    assert task_wrap == {'task_id': 'vmw903'}


async def test_delete_with_wait_polls_task_without_return_task_query(fake_http_client):
    # В отличие от vStack-шлюзов, ссылку на задачу удаление VMware отдаёт безусловно:
    # `return_task=true` здесь не нужен, и путь удаления с --wait тот же самый.
    fake_http_client.on('DELETE', NETWORK_PATH, {'task_id': 'vmw903'})
    fake_http_client.on('GET', 'api/v1/tasks/vmw903', task_response('vmw903', TaskState.completed))

    task_wrap = await VmwareNetworkService(fake_http_client).delete(NETWORK_ID, wait=True)

    assert fake_http_client.requests[0] == FakeRequest('DELETE', NETWORK_PATH)
    assert fake_http_client.paths('GET') == ['api/v1/tasks/vmw903']
    assert task_wrap is None


async def test_connect_servers_posts_nics_and_returns_task_per_server(fake_http_client):
    fake_http_client.on('POST', SERVERS_PATH, {'task_ids': ['vmw904', 'vmw905']})

    tasks_wrap = await VmwareNetworkService(fake_http_client).connect_servers(
        NETWORK_ID,
        nics=[VmwareServerNic(server_id=17), VmwareServerNic(server_id=18, ip='10.0.0.5')],
    )

    assert fake_http_client.requests == [FakeRequest('POST', SERVERS_PATH, {
        'nics': [{'server_id': 17, 'ip': None}, {'server_id': 18, 'ip': '10.0.0.5'}],
        'force_customization': False,
    })]
    assert tasks_wrap == {'task_ids': ['vmw904', 'vmw905']}


async def test_connect_servers_with_wait_polls_every_task(fake_http_client):
    fake_http_client.on('POST', SERVERS_PATH, {'task_ids': ['vmw904', 'vmw905']})
    fake_http_client.on('GET', 'api/v1/tasks/vmw904', task_response('vmw904', TaskState.completed))
    fake_http_client.on('GET', 'api/v1/tasks/vmw905', task_response('vmw905', TaskState.completed))
    fake_http_client.on('GET', NETWORK_PATH, {'network': NETWORK_ENTITY})

    network = await VmwareNetworkService(fake_http_client).connect_servers(
        NETWORK_ID,
        nics=[VmwareServerNic(server_id=17), VmwareServerNic(server_id=18)],
        force_customization=True,
        wait=True,
    )

    # Publisher порождает задачу на каждый сервер — дождаться нужно каждую.
    assert sorted(fake_http_client.paths('GET')) == sorted([
        'api/v1/tasks/vmw904', 'api/v1/tasks/vmw905', NETWORK_PATH,
    ])
    assert network == NETWORK_ENTITY
