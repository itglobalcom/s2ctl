from typing import ClassVar, Optional

from ssclient.base import BaseService, TaskIDWrap
from ssclient.gateway.gateway_id import GatewayId
from ssclient.ports import HttpClientPort


class GatewayPowerService(BaseService):
    _path: ClassVar[str] = 'api/v1/gateways/{gateway_id}'

    def __init__(self, http_client: HttpClientPort, gateway_id: GatewayId) -> None:
        super().__init__(http_client, {'gateway_id': gateway_id.value})

    async def start(self, wait: bool = False) -> Optional[TaskIDWrap]:
        return await self._send('start', wait)

    async def stop(self, wait: bool = False) -> Optional[TaskIDWrap]:
        return await self._send('stop', wait)

    async def restart(self, wait: bool = False) -> Optional[TaskIDWrap]:
        return await self._send('restart', wait)

    async def _send(self, action: str, wait: bool) -> Optional[TaskIDWrap]:
        task_wrap: TaskIDWrap = await self._http_client.post(
            path=self._make_path(action),
            payload={},
        )
        if wait:
            await self._wait_task_completion(self._task_id(task_wrap))
            return None
        return task_wrap
