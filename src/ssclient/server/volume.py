from typing import ClassVar, List, TypedDict, Union

from ssclient.base import BaseService, TaskIDWrap
from ssclient.ports import HttpClientPort


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
            task = await self._wait_task_completion(task_wrap['task_id'])
            return await self.get(task['volume_id'])
        return task_wrap

    async def get(self, volume_id: int) -> VolumeEntity:
        path = self._make_path(str(volume_id))
        volume_resp = await self._http_client.get(path)
        return volume_resp['volume']

    async def list(self) -> List[VolumeEntity]:  # noqa: WPS125
        volumes_resp = await self._http_client.get(self.path)
        return volumes_resp['volumes']

    async def update(
        self, volume_id: int, *, size_mb: int, wait: bool = False,
    ) -> Union[TaskIDWrap, VolumeEntity]:
        path = self._make_path(str(volume_id))
        task_wrap: TaskIDWrap = await self._http_client.put(
            path=path,
            payload={
                'size_mb': size_mb,
            },
        )
        if wait:
            task = await self._wait_task_completion(task_wrap['task_id'])
            return await self.get(task['volume_id'])
        return task_wrap

    async def delete(self, volume_id: int) -> None:
        path = self._make_path(str(volume_id))
        await self._http_client.delete(path)
