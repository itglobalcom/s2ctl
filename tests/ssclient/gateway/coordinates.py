"""Общие координаты маршрутов раздела шлюзов: составной id в пути и его сегменты."""

RAW_GATEWAY_ID = 'l1e2'
GATEWAYS_PATH = 'api/v1/gateways'
GATEWAY_PATH = '{path}/{gateway_id}'.format(path=GATEWAYS_PATH, gateway_id=RAW_GATEWAY_ID)
