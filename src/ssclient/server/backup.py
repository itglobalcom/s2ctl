from typing import AbstractSet, ClassVar, List, Optional, Union

from ssclient import errors
from ssclient.base import BaseService, Payload, TaskIDWrap, with_return_task
from ssclient.ports import HttpClientPort
from ssclient.server.backup_entities import (
    BackupScheduleEntity,
    BackupStoragesEntity,
    RestorePointEntity,
    RestorePointState,
    ServerBackupEntity,
)
from ssclient.server.server_id import ServerId
from ssclient.task_id import TaskId

_RESTORE_POINTS = 'restore-points'


class BackupService(BaseService):
    _path: ClassVar[str] = 'api/v1/servers/{server_id}/backup'

    def __init__(self, http_client: HttpClientPort, server_id: ServerId) -> None:
        super().__init__(http_client, {'server_id': server_id.value})

    async def storages(self) -> BackupStoragesEntity:
        return await self._http_client.get(self._make_path('storages'))

    async def get(self) -> ServerBackupEntity:
        return await self._http_client.get(self.path)

    async def enable(
        self, schedule: BackupScheduleEntity, wait: bool = False,
    ) -> Union[TaskIDWrap, ServerBackupEntity]:
        task_wrap: TaskIDWrap = await self._http_client.post(self.path, dict(schedule))
        if wait:
            await self._wait_task_completion(self._task_id(task_wrap))
            return await self.get()
        return task_wrap

    async def update(
        self, schedule: BackupScheduleEntity, wait: bool = False,
    ) -> Union[TaskIDWrap, ServerBackupEntity]:
        task_wrap: TaskIDWrap = await self._http_client.put(self.path, dict(schedule))
        if wait:
            await self._wait_task_completion(self._task_id(task_wrap))
            return await self.get()
        return task_wrap

    async def disable(self, wait: bool = False) -> Optional[TaskIDWrap]:
        task_wrap: TaskIDWrap = await self._http_client.delete(self.path)
        if wait:
            await self._wait_task_completion(self._task_id(task_wrap))
            return None
        return task_wrap

    async def list_restore_points(self) -> List[RestorePointEntity]:
        points_resp = await self._http_client.get(self._make_path(_RESTORE_POINTS))
        return points_resp['restore_points']

    async def create_restore_point(
        self, *, name: Optional[str] = None, wait: bool = False,
    ) -> Union[TaskIDWrap, RestorePointEntity]:
        payload: Payload = {} if name is None else {'name': name}
        if wait:
            return await self._take_restore_point(payload)
        return await self._http_client.post(self._make_path(_RESTORE_POINTS), payload)

    async def restore(self, restore_point_id: int, wait: bool = False) -> Optional[TaskIDWrap]:
        return await self._restore(restore_point_id, 'restore', {}, wait=wait)

    async def restore_nearby(
        self, restore_point_id: int, *, location_id: Optional[str] = None, wait: bool = False,
    ) -> Optional[TaskIDWrap]:
        payload: Payload = {} if location_id is None else {'location_id': location_id}
        return await self._restore(restore_point_id, 'restore-nearby', payload, wait=wait)

    async def delete_restore_point(self, restore_point_id: int, wait: bool = False) -> Optional[TaskIDWrap]:
        path = with_return_task(self._restore_point_path(restore_point_id))
        task_wrap: TaskIDWrap = await self._http_client.delete(path)
        if wait:
            await self._wait_task_completion(self._task_id(task_wrap))
            return None
        return task_wrap

    async def _restore(
        self, restore_point_id: int, action: str, payload: Payload, *, wait: bool,
    ) -> Optional[TaskIDWrap]:
        path = '{point_path}/{action}'.format(
            point_path=self._restore_point_path(restore_point_id), action=action,
        )
        task_wrap: TaskIDWrap = await self._http_client.post(path, payload)
        if wait:
            await self._wait_task_completion(self._task_id(task_wrap))
            return None
        return task_wrap

    async def _take_restore_point(self, payload: Payload) -> RestorePointEntity:
        known_ids = {_point_id(point) for point in await self.list_restore_points()}
        task_wrap: TaskIDWrap = await self._http_client.post(self._make_path(_RESTORE_POINTS), payload)
        task_id = self._task_id(task_wrap)
        await self._wait_task_completion(task_id)
        restore_point = _new_manual_point(await self.list_restore_points(), known_ids, task_id)
        if restore_point['state'] == RestorePointState.failed.value:
            raise errors.RestorePointFailedError(_point_id(restore_point), task_id.value)
        return restore_point

    def _restore_point_path(self, restore_point_id: int) -> str:
        return self._make_path('{points}/{point_id}'.format(points=_RESTORE_POINTS, point_id=restore_point_id))


def _new_manual_point(
    restore_points: List[RestorePointEntity], known_ids: AbstractSet[int], task_id: TaskId,
) -> RestorePointEntity:
    """Точка ручной копии: задача её id не публикует, поэтому точка — новая в списке сервера."""
    new_points = [
        point for point in restore_points
        if _point_id(point) not in known_ids and point['is_manual']
    ]
    if not new_points:
        raise errors.RestorePointMissingError(task_id.value)
    return max(new_points, key=_point_id)


def _point_id(restore_point: RestorePointEntity) -> int:
    return restore_point['id']
