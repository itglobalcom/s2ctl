from typing import ClassVar, Optional, TypedDict

from ssclient.base import BaseService, TaskIDWrap, with_return_task
from ssclient.gateway.gateway_id import GatewayId
from ssclient.network.network_id import NetworkId
from ssclient.ports import HttpClientPort


class GatewayNicEntity(TypedDict):
    id: int  # noqa: WPS125
    network_id: str
    ip_address: str
    bandwidth_mbps: int


class GatewayNicService(BaseService):
    _path: ClassVar[str] = 'api/v1/gateways/{gateway_id}/nics'

    def __init__(self, http_client: HttpClientPort, gateway_id: GatewayId) -> None:
        super().__init__(http_client, {'gateway_id': gateway_id.value})

    async def create(self, *, network_id: NetworkId, wait: bool = False) -> Optional[TaskIDWrap]:
        task_wrap: TaskIDWrap = await self._http_client.post(
            path=self.path,
            payload={
                'network_id': network_id.value,
            },
        )
        if wait:
            await self._wait_task_completion(self._task_id(task_wrap))
            return None
        return task_wrap

    async def delete(self, nic_id: int, wait: bool = False) -> Optional[TaskIDWrap]:
        path = with_return_task(self._make_path(str(nic_id)))
        task_wrap: TaskIDWrap = await self._http_client.delete(path)
        if wait:
            await self._wait_task_completion(self._task_id(task_wrap))
            return None
        return task_wrap
