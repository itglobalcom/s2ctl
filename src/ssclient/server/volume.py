from typing import ClassVar, List, Optional, TypedDict, Union

from ssclient.base import BaseService, TaskIDWrap, with_return_task
from ssclient.ports import HttpClientPort
from ssclient.task_entities import TaskResourceType, task_resource_id
from ssclient.task_id import TaskId


class VolumeEntity(TypedDict):
    id: int  # noqa: WPS125
    server_id: str
    name: str
    size_mb: int
    created: str


class VolumeService(BaseService):
    _path: ClassVar[str] = 'api/v1/servers/{server_id}/volumes'

    def __init__(self, http_client: HttpClientPort, server_id: str) -> None:
        super().__init__(http_client, {'server_id': server_id})

    async def create(
        self,
        *,
        name: str,
        size_mb: int,
        wait: bool = False,
    ) -> Union[TaskIDWrap, VolumeEntity]:
        task_wrap: TaskIDWrap = await self._http_client.post(
            path=self.path,
            payload={
                'name': name,
                'size_mb': size_mb,
            },
        )
        if wait:
            task = await self._wait_task_completion(TaskId.parse(task_wrap['task_id']))
            return await self.get(int(task_resource_id(task, TaskResourceType.volume)))
        return task_wrap

    async def get(self, volume_id: int) -> VolumeEntity:
        path = self._make_path(str(volume_id))
        volume_resp = await self._http_client.get(path)
        return volume_resp['volume']

    async def list(self) -> List[VolumeEntity]:  # noqa: WPS125
        volumes_resp = await self._http_client.get(self.path)
        return volumes_resp['volumes']

    async def update(
        self,
        volume_id: int,
        *,
        size_mb: int,
        name: Optional[str] = None,
        wait: bool = False,
    ) -> Union[TaskIDWrap, VolumeEntity]:
        path = self._make_path(str(volume_id))
        # Размер обязателен: `VstackEditVolumeCommand.SizeMb` — не-nullable `int`
        # с `[EncodedRange(1, …)]`, и на пропущенном поле publisher отвечает 400.
        # Имя не передано — publisher оставляет диску текущее.
        task_wrap: TaskIDWrap = await self._http_client.put(
            path=path,
            payload={
                'name': name,
                'size_mb': size_mb,
            },
        )
        if wait:
            task = await self._wait_task_completion(TaskId.parse(task_wrap['task_id']))
            return await self.get(int(task_resource_id(task, TaskResourceType.volume)))
        return task_wrap

    async def delete(self, volume_id: int, wait: bool = False) -> Optional[TaskIDWrap]:
        path = with_return_task(self._make_path(str(volume_id)))
        task_wrap: TaskIDWrap = await self._http_client.delete(path)
        if wait:
            await self._wait_task_completion(self._task_id(task_wrap))
            return None
        return task_wrap
