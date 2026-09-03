"""Общие координаты маршрутов услуги VMware: сеть и её edge адресуются числовым id."""

NETWORK_ID = 42

NETWORKS_PATH = 'api/v1/vmware/networks'
NETWORK_PATH = '{path}/{network_id}'.format(path=NETWORKS_PATH, network_id=NETWORK_ID)
EDGE_PATH = '{network_path}/edge'.format(network_path=NETWORK_PATH)

NETWORK_ENTITY = {
    'id': NETWORK_ID,
    'location_id': 1,
    'type': 'routed_client',
    'name': 'net',
    'address': '10.0.0.0',
    'mask': 24,
    'gateway': '10.0.0.1',
    'bandwidth_mbps': 100,
    'is_dhcp': False,
    'shared': False,
    'state': 'Active',
    'nics_count': 0,
}
