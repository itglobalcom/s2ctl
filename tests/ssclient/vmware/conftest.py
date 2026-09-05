"""Общие координаты маршрутов услуги VMware: сеть с её edge и сервер адресуются числовым id."""

NETWORK_ID = 42

NETWORKS_PATH = 'api/v1/vmware/networks'
NETWORK_PATH = '{path}/{network_id}'.format(path=NETWORKS_PATH, network_id=NETWORK_ID)
EDGE_PATH = '{network_path}/edge'.format(network_path=NETWORK_PATH)

# Поля, без которых `PUT /api/v1/vmware/networks/{network_id}` отвечает 400: обязательным
# имя делает доменная команда правки publisher'а, а не модель запроса — та не помечает
# обязательным ничего. Своё текущее имя publisher в запрос не подставляет.
EDIT_NETWORK_REQUIRED_FIELDS = frozenset(('name',))

NETWORK_ENTITY = {
    'id': NETWORK_ID,
    'location_id': 1,
    'type': 'routed_client',
    'name': 'net',
    'address': '10.0.0.0',
    'mask': 24,
    'gateway': '10.0.0.1',
    'edge_external_ip': '198.51.100.10',
    'bandwidth_mbps': 100,
    'is_dhcp': False,
    'shared': False,
    'state': 'Active',
    'nics_count': 0,
}

SERVER_ID = 100

SERVERS_PATH = 'api/v1/vmware/servers'
SERVER_PATH = '{path}/{server_id}'.format(path=SERVERS_PATH, server_id=SERVER_ID)

VOLUME_ID = 7
NIC_ID = 3

VOLUMES_PATH = '{server_path}/volumes'.format(server_path=SERVER_PATH)
VOLUME_PATH = '{path}/{volume_id}'.format(path=VOLUMES_PATH, volume_id=VOLUME_ID)

NICS_PATH = '{server_path}/nics'.format(server_path=SERVER_PATH)
NIC_PATH = '{path}/{nic_id}'.format(path=NICS_PATH, nic_id=NIC_ID)
# Общая сеть подключается своим маршрутом: это отдельная операция контракта, а не
# признак в теле запроса к маршруту клиентской сети.
SHARED_NICS_PATH = '{path}/shared'.format(path=NICS_PATH)

# Снимок VMware-сервера один и адресуется самим сервером — сегмента с id снимка в пути нет.
SNAPSHOT_PATH = '{server_path}/snapshot'.format(server_path=SERVER_PATH)
