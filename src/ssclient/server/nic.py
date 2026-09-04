from typing import ClassVar, List, Optional, TypedDict, Union

from ssclient.base import BaseService, TaskIDWrap, with_return_task
from ssclient.network.network_id import NetworkId
from ssclient.ports import HttpClientPort
from ssclient.task_entities import TaskResourceType, task_resource_id
from ssclient.task_id import TaskId


class NicEntity(TypedDict):
    id: int  # noqa: WPS125
    server_id: str
    mac: str
    ip_address: str
    mask: int
    bandwidth_mbps: int


class NicService(BaseService):
    _path: ClassVar[str] = 'api/v1/servers/{server_id}/nics'

    def __init__(self, http_client: HttpClientPort, server_id: str) -> None:
        super().__init__(http_client, {'server_id': server_id})

    async def create(
        self, *, network_id: Optional[NetworkId], bandwidth: Optional[int], wait: bool = False,
    ) -> Union[TaskIDWrap, NicEntity]:
        task_wrap: TaskIDWrap = await self._http_client.post(
            path=self.path,
            payload={
                'network_id': network_id.value if network_id else None,
                'bandwidth_mbps': bandwidth,
            },
        )
        if wait:
            task = await self._wait_task_completion(TaskId.parse(task_wrap['task_id']))
            return await self.get(int(task_resource_id(task, TaskResourceType.nic)))

        return task_wrap

    async def get(self, nic_id: int) -> NicEntity:
        path = self._make_path(str(nic_id))
        nic_resp = await self._http_client.get(path)
        return nic_resp['nic']

    async def list(self) -> List[NicEntity]:  # noqa: WPS125
        nics_resp = await self._http_client.get(self.path)
        return nics_resp['nics']

    async def update(
        self, nic_id: int, *, bandwidth_mbps: int, wait: bool = False,
    ) -> Union[TaskIDWrap, NicEntity]:
        path = self._make_path(str(nic_id))
        task_wrap: TaskIDWrap = await self._http_client.put(
            path=path,
            payload={
                'bandwidth_mbps': bandwidth_mbps,
            },
        )
        if wait:
            await self._wait_task_completion(self._task_id(task_wrap))
            return await self.get(nic_id)
        return task_wrap

    async def delete(self, nic_id: int, wait: bool = False) -> Optional[TaskIDWrap]:
        path = with_return_task(self._make_path(str(nic_id)))
        task_wrap: TaskIDWrap = await self._http_client.delete(path)
        if wait:
            await self._wait_task_completion(self._task_id(task_wrap))
            return None
        return task_wrap
