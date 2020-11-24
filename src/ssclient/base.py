import asyncio
from typing import Any, ClassVar, Dict, Optional, TypedDict
from urllib.parse import urljoin

from async_timeout import timeout

from ssclient import errors
from ssclient.ports import HttpClientPort

URLFields = Dict[str, Any]


class TaskIDWrap(TypedDict):
    task_id: str


class BaseTaskEntity(TypedDict):
    id: str  # noqa: WPS125
    server_id: str
    created: str
    completed: str
    is_completed: str


class TaskEntity(BaseTaskEntity, total=False):
    server_id: str
    location_id: str
    network_id: str
    volume_id: int
    nic_id: int
    snapshot_id: int


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

    def _make_path(self, fragment: str) -> str:
        path = self.path
        if not path.endswith('/'):
            path = '{path}/'.format(path=path)
        return urljoin(path, fragment)

    async def _wait_task_completion(self, task_id: str, timeout_secs: int = 60) -> TaskEntity:
        async with timeout(timeout_secs):
            while True:
                path = urljoin('api/v1/tasks/', task_id)
                task_resp = await self._http_client.get(path)
                task_data = task_resp['task']
                status = task_data['is_completed']
                if status == 'Completed':
                    return task_data
                elif status == 'Failed':
                    raise errors.TaskFailedError(task_id)
                await asyncio.sleep(1)
