import pytest

from ssclient import errors
from ssclient.base import TASKS_PATH, BaseService
from ssclient.task import TaskService
from ssclient.task_entities import TaskState
from ssclient.task_id import TaskId
from tests.conftest import task_response

# Опрос идёт раз в секунду, поэтому ожидание в тестах ограничено парой опросов:
# сломанное условие терминального статуса упирается в таймаут, а не висит минуту.
WAIT_TIMEOUT_SECS = 2

TASK_IDS_OF_EVERY_FORMAT = ('l2t345', 'lt345', 'dns42', 'vmw7')


class _TaskWaiter(BaseService):
    """Наследник BaseService без своей логики.

    Ожидание задачи — контракт базового сервиса для всех услуг, отдельного публичного
    носителя у него нет: услуги вызывают его из своих операций с `--wait`.
    """

    _path = TASKS_PATH

    async def wait(self, raw_id: str, timeout_secs: int = WAIT_TIMEOUT_SECS):
        return await self._wait_task_completion(TaskId.parse(raw_id), timeout_secs)


def _task_path(raw_id: str) -> str:
    return '{tasks_path}/{raw_id}'.format(tasks_path=TASKS_PATH, raw_id=raw_id)


@pytest.mark.parametrize('raw_id', TASK_IDS_OF_EVERY_FORMAT)
async def test_get_requests_task_path_of_every_format(raw_id, fake_http_client):
    # Маршрут чтения задачи один на все услуги, различается только подстановка id.
    fake_http_client.on(
        'GET', _task_path(raw_id), task_response(raw_id, TaskState.completed),
    )

    task = await TaskService(fake_http_client).get(TaskId.parse(raw_id))

    assert fake_http_client.paths('GET') == [_task_path(raw_id)]
    assert task['id'] == raw_id


async def test_wait_polls_until_task_is_completed(fake_http_client):
    fake_http_client.on(
        'GET', _task_path('l2t345'),
        task_response('l2t345', TaskState.in_progress),
        task_response('l2t345', TaskState.completed, resources=[('server', 'l2s99')]),
    )

    task = await _TaskWaiter(fake_http_client).wait('l2t345', timeout_secs=10)

    assert task['is_completed'] == TaskState.completed.value
    assert task['resources'] == [{'type': 'server', 'id': 'l2s99'}]
    assert len(fake_http_client.paths('GET')) == 2


@pytest.mark.parametrize('state', [TaskState.failed, TaskState.canceled])
async def test_wait_fails_on_terminal_unsuccessful_state(state, fake_http_client):
    # Canceled терминален так же, как Failed: до этой фазы отменённая задача
    # опрашивалась до самого таймаута вместо ошибки.
    fake_http_client.on('GET', _task_path('dns42'), task_response('dns42', state))

    with pytest.raises(errors.TaskFailedError) as exc_info:
        await _TaskWaiter(fake_http_client).wait('dns42')

    assert exc_info.value.task_id == 'dns42'
    assert exc_info.value.state == state.value


async def test_wait_timeout_names_task_and_waited_seconds(fake_http_client):
    fake_http_client.on(
        'GET', _task_path('l2t345'), task_response('l2t345', TaskState.in_progress),
    )

    with pytest.raises(errors.TaskWaitTimeoutError) as exc_info:
        await _TaskWaiter(fake_http_client).wait('l2t345')

    assert exc_info.value.task_id == 'l2t345'
    assert exc_info.value.timeout_secs == WAIT_TIMEOUT_SECS
    assert fake_http_client.paths('GET')


async def test_always_completed_task_is_not_polled(fake_http_client):
    # Синтетической задачи на стороне publisher'а нет — опрашивать её нечем.
    task = await _TaskWaiter(fake_http_client).wait('already_completed_task')

    assert task['id'] == 'already_completed_task'
    assert task['is_completed'] == TaskState.completed.value
    assert fake_http_client.requests == []
