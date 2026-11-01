import datetime

import pytest

from ssclient.project import ProjectService

CONSUMPTION_PATH = 'api/v1/project/consumption'

RESOURCES_PATH = 'api/v1/project/consumption/resources'

DAILY_PATH = 'api/v1/project/consumption/daily'

_PERIOD = {
    'from': '2026-10-01',
    'to': '2026-10-31',
    'time_zone': 'Europe/Moscow',
    'currency': 'RUB',
    'is_final': True,
    'total': 1250.5,
}

SERVICES_CONSUMPTION = {**_PERIOD, 'services': [
    {'service': 'vstack', 'total': 1000.25},
    {'service': 'llm', 'total': 250.25},
]}

# Шлюз vStack приходит без `id`, ручное списание — без `id` и `name`: поля без значения
# publisher опускает, а не отдаёт `null`.
RESOURCES_CONSUMPTION = {**_PERIOD, 'resources': [
    {'service': 'vstack', 'type': 'vstack_server', 'id': 'l1s12345', 'name': 'web-1', 'total': 900.25},
    {'service': 'vstack', 'type': 'vstack_edge', 'name': 'edge-1', 'total': 100},
    {'service': 'llm', 'type': 'manual_billing', 'total': 250.25},
]}

DAILY_CONSUMPTION = {**_PERIOD, 'days': [
    {'date': '2026-10-01', 'total': 1250.5},
    {'date': '2026-10-02', 'total': 0},
]}

_OCT_1 = datetime.date(2026, 10, 1)
_OCT_31 = datetime.date(2026, 10, 31)

_CONSUMPTION_CASES = (
    ('consumption', CONSUMPTION_PATH, SERVICES_CONSUMPTION),
    ('consumption_resources', RESOURCES_PATH, RESOURCES_CONSUMPTION),
    ('consumption_daily', DAILY_PATH, DAILY_CONSUMPTION),
)


@pytest.mark.parametrize('method,path,envelope', _CONSUMPTION_CASES)
async def test_consumption_is_unwrapped_without_the_period_by_default(
    fake_http_client, method, path, envelope,
):
    fake_http_client.on('GET', path, {'consumption': envelope})

    consumption = await getattr(ProjectService(fake_http_client), method)()

    assert fake_http_client.paths('GET') == [path]
    assert consumption == envelope


@pytest.mark.parametrize('method,path,envelope', _CONSUMPTION_CASES)
async def test_consumption_passes_the_period_to_the_query_of_the_contract(
    fake_http_client, method, path, envelope,
):
    expected_path = '{path}?from=2026-10-01&to=2026-10-31'.format(path=path)
    fake_http_client.on('GET', expected_path, {'consumption': envelope})

    await getattr(ProjectService(fake_http_client), method)(_OCT_1, _OCT_31)

    assert fake_http_client.paths('GET') == [expected_path]


_RESOURCES_FILTER_CASES = (
    ({'period_to': _OCT_31}, '{path}?to=2026-10-31'.format(path=RESOURCES_PATH)),
    ({'service': 'cloud_director'}, '{path}?service=cloud_director'.format(path=RESOURCES_PATH)),
    (
        {'period_from': _OCT_1, 'service': 'vstack'},
        '{path}?from=2026-10-01&service=vstack'.format(path=RESOURCES_PATH),
    ),
)


@pytest.mark.parametrize('filters,expected_path', _RESOURCES_FILTER_CASES)
async def test_consumption_resources_passes_each_filter_on_its_own(
    fake_http_client, filters, expected_path,
):
    fake_http_client.on('GET', expected_path, {'consumption': RESOURCES_CONSUMPTION})

    await ProjectService(fake_http_client).consumption_resources(**filters)

    assert fake_http_client.paths('GET') == [expected_path]
