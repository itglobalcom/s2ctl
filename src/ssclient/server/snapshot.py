from typing import ClassVar, List, Optional, TypedDict

from ssclient.base import BaseService, TaskIDWrap, with_return_task
from ssclient.ports import HttpClientPort
from ssclient.task_id import TaskId


class SnapshotEntity(TypedDict):
    id: int  # noqa: WPS125
    server_id: str
    name: str
    size_mb: int
    created: str


class SnapshotService(BaseService):
    _path: ClassVar[str] = 'api/v1/servers/{server_id}/snapshots'

    def __init__(self, http_client: HttpClientPort, server_id: str) -> None:
        super().__init__(http_client, {'server_id': server_id})

    async def create(self, *, name: str, wait: bool = False) -> Optional[TaskIDWrap]:
        task_wrap: TaskIDWrap = await self._http_client.post(
            path=self.path,
            payload={
                'name': name,
            },
        )
        if wait:
            await self._wait_task_completion(TaskId.parse(task_wrap['task_id']))
            return None
        return task_wrap

    async def get(self, snapshot_id: int) -> SnapshotEntity:
        path = self._make_path(str(snapshot_id))
        snap_resp = await self._http_client.get(path)
        return snap_resp['snapshot']

    async def list(self) -> List[SnapshotEntity]:  # noqa: WPS125
        snaps_resp = await self._http_client.get(self.path)
        return snaps_resp['snapshots']

    async def delete(self, snapshot_id: int, wait: bool = False) -> Optional[TaskIDWrap]:
        path = with_return_task(self._make_path(str(snapshot_id)))
        task_wrap: TaskIDWrap = await self._http_client.delete(path)
        if wait:
            await self._wait_task_completion(self._task_id(task_wrap))
            return None
        return task_wrap

    async def rollback(self, snapshot_id: int, wait: bool = False) -> Optional[TaskIDWrap]:
        fragment = '{snap_id}/rollback'.format(snap_id=snapshot_id)
        path = self._make_path(fragment)
        task_wrap: TaskIDWrap = await self._http_client.post(path, {})
        if wait:
            await self._wait_task_completion(TaskId.parse(task_wrap['task_id']))
            return None
        return task_wrap
