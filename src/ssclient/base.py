import asyncio
from typing import Any, ClassVar, Dict, Optional, TypedDict
from urllib.parse import urljoin

from async_timeout import timeout

from ssclient import errors
from ssclient.ports import HttpClientPort
from ssclient.task_entities import TaskEntity, TaskState, completed_task
from ssclient.task_id import TaskId

URLFields = Dict[str, Any]

TASKS_PATH = 'api/v1/tasks'
DEFAULT_TASK_TIMEOUT = 60
_POLL_INTERVAL_SECS = 1
_FAILURE_STATES = frozenset((TaskState.failed, TaskState.canceled))
_RETURN_TASK_QUERY = 'return_task=true'


class TaskIDWrap(TypedDict):
    task_id: str


def task_path(task_id: TaskId) -> str:
    return '{tasks_path}/{task_id}'.format(tasks_path=TASKS_PATH, task_id=task_id.value)


def with_return_task(path: str) -> str:
    """Путь удаления, по которому publisher отдаёт ссылку на задачу: без параметра ответ пуст."""
    return '{path}?{query}'.format(path=path, query=_RETURN_TASK_QUERY)


class BaseService(object):
    _path: ClassVar[str]

    def __init__(
        self, http_client: HttpClientPort, url_fields: Optional[URLFields] = None,
    ):
        self._http_client = http_client
        if url_fields:
            self._url_fields = url_fields
        else:
            self._url_fields = {}

    @property
    def path(self) -> str:
        return self._path.format_map(self._url_fields)

    def _task_id(self, task_wrap: TaskIDWrap) -> TaskId:
        return TaskId.parse(task_wrap['task_id'])

    def _make_path(self, fragment: str) -> str:
        path = self.path
        if not path.endswith('/'):
            path = '{path}/'.format(path=path)
        return urljoin(path, fragment)

    async def _wait_task_completion(
        self, task_id: TaskId, timeout_secs: int = DEFAULT_TASK_TIMEOUT,
    ) -> TaskEntity:
        if task_id.is_always_completed:
            return completed_task(task_id.value)

        try:
            async with timeout(timeout_secs):
                return await self._poll_task(task_id)
        except asyncio.TimeoutError as exc:
            raise errors.TaskWaitTimeoutError(task_id.value, timeout_secs) from exc

    async def _poll_task(self, task_id: TaskId) -> TaskEntity:
        while True:
            task_resp = await self._http_client.get(task_path(task_id))
            task_data = task_resp['task']
            state = TaskState(task_data['is_completed'])
            if state == TaskState.completed:
                return task_data
            elif state in _FAILURE_STATES:
                raise errors.TaskFailedError(task_id.value, state.value)
            await asyncio.sleep(_POLL_INTERVAL_SECS)
