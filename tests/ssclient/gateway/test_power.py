import pytest

from ssclient.gateway.power import GatewayPowerService
from ssclient.task_entities import TaskState
from tests.conftest import FakeRequest, task_response
from tests.ssclient.gateway.conftest import GATEWAY_PATH

# Три состояния питания — три отдельных маршрута publisher'а. Склейки вида
# «stop с флагом hard» в контракте нет: флаг режима превратил бы три юзкейса в один.
POWER_OPERATIONS = (
    ('start', '{gateway_path}/start'.format(gateway_path=GATEWAY_PATH)),
    ('stop', '{gateway_path}/stop'.format(gateway_path=GATEWAY_PATH)),
    ('restart', '{gateway_path}/restart'.format(gateway_path=GATEWAY_PATH)),
)


@pytest.mark.parametrize('operation_name,expected_path', POWER_OPERATIONS)
async def test_each_power_operation_posts_to_its_own_route(
    fake_http_client, gateway_id, operation_name, expected_path,
):
    fake_http_client.on('POST', expected_path, {'task_id': 'l1t345'})
    power_service = GatewayPowerService(fake_http_client, gateway_id)

    task_wrap = await getattr(power_service, operation_name)()

    assert fake_http_client.requests == [FakeRequest('POST', expected_path, {})]
    assert task_wrap == {'task_id': 'l1t345'}


async def test_power_operation_with_wait_polls_task_and_returns_nothing(
    fake_http_client, gateway_id,
):
    start_path = '{gateway_path}/start'.format(gateway_path=GATEWAY_PATH)
    fake_http_client.on('POST', start_path, {'task_id': 'l1t345'})
    fake_http_client.on('GET', 'api/v1/tasks/l1t345', task_response('l1t345', TaskState.completed))

    task_wrap = await GatewayPowerService(fake_http_client, gateway_id).start(wait=True)

    assert fake_http_client.paths('GET') == ['api/v1/tasks/l1t345']
    assert task_wrap is None
