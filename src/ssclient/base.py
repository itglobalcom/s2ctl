import asyncio
from typing import Any, ClassVar, Dict, Mapping, Optional, TypedDict
from urllib.parse import urlencode, urljoin

from ssclient import errors
from ssclient.ports import HttpClientPort
from ssclient.task_entities import TaskEntity, TaskState, completed_task
from ssclient.task_id import TaskId
from ssclient.task_wait import task_timeout_secs

URLFields = Dict[str, Any]
Payload = Dict[str, Any]

TASKS_PATH = 'api/v1/tasks'
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


def with_filters(path: str, filters: Mapping[str, Any]) -> str:
    """Путь с непустыми фильтрами: на пустое значение объявленного параметра publisher отвечает 500."""
    query = {name: raw_filter for name, raw_filter in filters.items() if raw_filter is not None}
    if not query:
        return path
    return '{path}?{query}'.format(path=path, query=urlencode(query))


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
        self, task_id: TaskId, timeout_secs: Optional[int] = None,
    ) -> TaskEntity:
        if task_id.is_always_completed:
            return completed_task(task_id.value)

        wait_secs = task_timeout_secs() if timeout_secs is None else timeout_secs
        try:
            async with asyncio.timeout(wait_secs):
                return await self._poll_task(task_id)
        except asyncio.TimeoutError as exc:
            raise errors.TaskWaitTimeoutError(task_id.value, wait_secs) from exc

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
