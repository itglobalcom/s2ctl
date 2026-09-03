from typing import ClassVar, Optional

from ssclient.base import BaseService, TaskIDWrap
from ssclient.ports import HttpClientPort
from ssclient.vmware.ids import VmwareServerId


class VmwareServerPowerService(BaseService):
    """Питание VMware-сервера: у каждого перехода свой маршрут контракта."""

    _path: ClassVar[str] = 'api/v1/vmware/servers/{server_id}/power'

    def __init__(self, http_client: HttpClientPort, server_id: VmwareServerId) -> None:
        super().__init__(http_client, {'server_id': server_id})

    async def power_on(self, wait: bool = False) -> Optional[TaskIDWrap]:
        return await self._power('on', wait=wait)

    async def power_off(self, wait: bool = False) -> Optional[TaskIDWrap]:
        return await self._power('off', wait=wait)

    async def shutdown(self, wait: bool = False) -> Optional[TaskIDWrap]:
        return await self._power('shutdown', wait=wait)

    async def reboot(self, wait: bool = False) -> Optional[TaskIDWrap]:
        return await self._power('reboot', wait=wait)

    async def reset(self, wait: bool = False) -> Optional[TaskIDWrap]:
        return await self._power('reset', wait=wait)

    async def _power(self, transition: str, *, wait: bool) -> Optional[TaskIDWrap]:
        task_wrap: TaskIDWrap = await self._http_client.post(
            path=self._make_path(transition),
            payload={},
        )
        if wait:
            await self._wait_task_completion(self._task_id(task_wrap))
            return None
        return task_wrap
