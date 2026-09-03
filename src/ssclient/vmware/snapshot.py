from typing import ClassVar, Optional, TypedDict, Union

from ssclient.base import BaseService, TaskIDWrap
from ssclient.ports import HttpClientPort

_RESTORE_FRAGMENT = 'restore'


class VmwareServerSnapshotEntity(TypedDict):
    name: str
    created: str


class VmwareServerSnapshotService(BaseService):
    """Снимок VMware-сервера один, и контракт адресует его сервером, без id снимка."""

    _path: ClassVar[str] = 'api/v1/vmware/servers/{server_id}/snapshot'

    def __init__(self, http_client: HttpClientPort, server_id: int) -> None:
        super().__init__(http_client, {'server_id': server_id})

    async def get(self) -> Optional[VmwareServerSnapshotEntity]:
        # Сервер без снимка — не ошибка: publisher отвечает 200 и `snapshot: null`.
        snapshot_resp = await self._http_client.get(self.path)
        return snapshot_resp['snapshot']

    async def create(
        self, *, name: str, wait: bool = False,
    ) -> Union[TaskIDWrap, VmwareServerSnapshotEntity, None]:
        task_wrap: TaskIDWrap = await self._http_client.post(
            path=self.path,
            payload={'name': name},
        )
        if not wait:
            return task_wrap
        await self._wait_task_completion(self._task_id(task_wrap))
        return await self.get()

    async def restore(self, wait: bool = False) -> Optional[TaskIDWrap]:
        task_wrap: TaskIDWrap = await self._http_client.post(
            path=self._make_path(_RESTORE_FRAGMENT),
            payload={},
        )
        if wait:
            await self._wait_task_completion(self._task_id(task_wrap))
            return None
        return task_wrap

    async def delete(self, wait: bool = False) -> Optional[TaskIDWrap]:
        # Удаление снимка VMware отдаёт ссылку на задачу само, без `return_task=true`.
        task_wrap: TaskIDWrap = await self._http_client.delete(self.path)
        if wait:
            await self._wait_task_completion(self._task_id(task_wrap))
            return None
        return task_wrap
