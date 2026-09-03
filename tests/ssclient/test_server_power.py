"""Питание vStack-сервера: у каждого перехода свой маршрут и своя задача.

Регресс на миграцию ожидания задачи: пять переходов ждут её одинаково, и ошибка
в любом из них видна только в рантайме.
"""
import pytest

from ssclient.server.power import ServerPowerService
from ssclient.task_entities import TaskState
from tests.conftest import FakeRequest, task_response

POWER_PATH = 'api/v1/servers/l2s99/power'

TRANSITIONS = (
    ('power_on', 'on'),
    ('power_off', 'off'),
    ('shutdown', 'shutdown'),
    ('reboot', 'reboot'),
    ('reset', 'reset'),
)


@pytest.mark.parametrize('method_name,fragment', TRANSITIONS)
async def test_transition_posts_its_own_route_and_returns_task(
    fake_http_client, method_name, fragment,
):
    path = '{power_path}/{fragment}'.format(power_path=POWER_PATH, fragment=fragment)
    fake_http_client.on('POST', path, {'task_id': 'l2t345'})

    task_wrap = await getattr(ServerPowerService(fake_http_client, 'l2s99'), method_name)()

    assert fake_http_client.requests == [FakeRequest('POST', path, {})]
    assert task_wrap == {'task_id': 'l2t345'}


@pytest.mark.parametrize('method_name,fragment', TRANSITIONS)
async def test_transition_with_wait_polls_the_task(fake_http_client, method_name, fragment):
    path = '{power_path}/{fragment}'.format(power_path=POWER_PATH, fragment=fragment)
    fake_http_client.on('POST', path, {'task_id': 'l2t345'})
    fake_http_client.on('GET', 'api/v1/tasks/l2t345', task_response('l2t345', TaskState.completed))

    power_service = ServerPowerService(fake_http_client, 'l2s99')
    task_wrap = await getattr(power_service, method_name)(wait=True)

    assert fake_http_client.paths('GET') == ['api/v1/tasks/l2t345']
    assert task_wrap is None
