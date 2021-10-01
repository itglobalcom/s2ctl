from typing import ClassVar, List, Optional, TypedDict, Union

from ssclient.base import BaseService, TaskIDWrap
from ssclient.ports import HttpClientPort


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
        self, *, network_id: Optional[str], bandwidth: Optional[int], wait: bool = False,
    ) -> Union[TaskIDWrap, NicEntity]:
        task_wrap: TaskIDWrap = await self._http_client.post(
            path=self.path,
            payload={
                'network_id': network_id,
                'bandwidth_mbps': bandwidth,
            },
        )
        if wait:
            task = await self._wait_task_completion(task_wrap['task_id'])
            return await self.get(task['nic_id'])

        return task_wrap

    async def get(self, nic_id: int) -> NicEntity:
        path = self._make_path(str(nic_id))
        nic_resp = await self._http_client.get(path)
        return nic_resp['nic']

    async def list(self) -> List[NicEntity]:  # noqa: WPS125
        nics_resp = await self._http_client.get(self.path)
        return nics_resp['nics']

    async def delete(self, nic_id: int, wait: bool = False) -> None:
        path = self._make_path(str(nic_id))
        await self._http_client.delete(path)
