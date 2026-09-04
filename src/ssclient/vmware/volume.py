from typing import ClassVar, List, Optional, TypedDict, Union

from ssclient.base import BaseService, TaskIDWrap
from ssclient.ports import HttpClientPort
from ssclient.vmware.ids import VmwareServerId, VmwareVolumeId


class VmwareServerVolumeEntity(TypedDict):
    id: int
    name: str
    size_mb: int
    disk_type: str


class VmwareServerVolumeService(BaseService):
    """Дополнительные диски VMware-сервера; системный диск — часть конфигурации сервера."""

    _path: ClassVar[str] = 'api/v1/vmware/servers/{server_id}/volumes'

    def __init__(self, http_client: HttpClientPort, server_id: VmwareServerId) -> None:
        super().__init__(http_client, {'server_id': server_id})

    async def list(self) -> List[VmwareServerVolumeEntity]:
        volumes_resp = await self._http_client.get(self.path)
        return volumes_resp['volumes']

    async def get(self, volume_id: VmwareVolumeId) -> VmwareServerVolumeEntity:
        volume_resp = await self._http_client.get(self._volume_path(volume_id))
        return volume_resp['volume']

    async def create(
        self, *, name: str, disk_type: str, size_mb: int, wait: bool = False,
    ) -> Union[TaskIDWrap, List[VmwareServerVolumeEntity]]:
        task_wrap: TaskIDWrap = await self._http_client.post(
            path=self.path,
            payload={
                'name': name,
                'disk_type': disk_type,
                'size_mb': size_mb,
            },
        )
        if not wait:
            return task_wrap
        await self._wait_task_completion(self._task_id(task_wrap))
        # Ни ответ операции, ни `resources[]` VMware-задачи не несут id созданного диска:
        # задача публикует ресурсы только двух типов, server и network.
        return await self.list()

    async def edit(
        self,
        volume_id: VmwareVolumeId,
        *,
        size_mb: int,
        name: Optional[str] = None,
        wait: bool = False,
    ) -> Union[TaskIDWrap, VmwareServerVolumeEntity]:
        # Имя не передано — publisher оставляет диску текущее.
        task_wrap: TaskIDWrap = await self._http_client.put(
            path=self._volume_path(volume_id),
            payload={
                'name': name,
                'size_mb': size_mb,
            },
        )
        if not wait:
            return task_wrap
        await self._wait_task_completion(self._task_id(task_wrap))
        return await self.get(volume_id)

    async def delete(self, volume_id: VmwareVolumeId, wait: bool = False) -> Optional[TaskIDWrap]:
        # Удаление диска VMware отдаёт ссылку на задачу само, без `return_task=true`.
        task_wrap: TaskIDWrap = await self._http_client.delete(self._volume_path(volume_id))
        if wait:
            await self._wait_task_completion(self._task_id(task_wrap))
            return None
        return task_wrap

    def _volume_path(self, volume_id: VmwareVolumeId) -> str:
        return self._make_path(str(volume_id))
