import pytest

from ssclient.task_entities import TaskState
from ssclient.vmware.power import VmwareServerPowerService
from tests.conftest import FakeRequest, task_response
from tests.ssclient.vmware.conftest import SERVER_ID, SERVER_PATH

POWER_PATH = '{server_path}/power'.format(server_path=SERVER_PATH)

# Пять переходов питания — пять маршрутов publisher'а, по методу на каждый. Склейки
# «off с флагом hard», как у легаси-раздела vStack, здесь нет и быть не должно:
# флаг режима превратил бы два юзкейса (обесточить и погасить гостевую ОС) в один.
POWER_OPERATIONS = (
    ('power_on', '{path}/on'.format(path=POWER_PATH)),
    ('power_off', '{path}/off'.format(path=POWER_PATH)),
    ('shutdown', '{path}/shutdown'.format(path=POWER_PATH)),
    ('reboot', '{path}/reboot'.format(path=POWER_PATH)),
    ('reset', '{path}/reset'.format(path=POWER_PATH)),
)


@pytest.mark.parametrize('method_name,expected_path', POWER_OPERATIONS)
async def test_each_power_operation_posts_to_its_own_route(
    fake_http_client, method_name, expected_path,
):
    fake_http_client.on('POST', expected_path, {'task_id': 'vmw55'})
    power_service = VmwareServerPowerService(fake_http_client, SERVER_ID)

    task_wrap = await getattr(power_service, method_name)()

    assert fake_http_client.requests == [FakeRequest('POST', expected_path, {})]
    assert task_wrap == {'task_id': 'vmw55'}


async def test_power_operation_with_wait_polls_task_and_returns_nothing(fake_http_client):
    off_path = '{path}/off'.format(path=POWER_PATH)
    fake_http_client.on('POST', off_path, {'task_id': 'vmw55'})
    fake_http_client.on('GET', 'api/v1/tasks/vmw55', task_response('vmw55', TaskState.completed))

    task_wrap = await VmwareServerPowerService(fake_http_client, SERVER_ID).power_off(wait=True)

    assert fake_http_client.paths('GET') == ['api/v1/tasks/vmw55']
    assert task_wrap is None
