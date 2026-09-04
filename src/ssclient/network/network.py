from typing import ClassVar, List, Optional, TypedDict, Union

from ssclient.base import BaseService, TaskIDWrap, with_return_task
from ssclient.network.network_id import NetworkId
from ssclient.network.tag import TagService
from ssclient.task_entities import TaskResourceType, task_resource_id
from ssclient.task_id import TaskId


class NetworkEntity(TypedDict):
    id: str  # noqa: WPS125
    location_id: str
    name: str
    description: str
    network_prefix: str
    mask: int
    server_ids: List[str]
    state: str
    created: str
    tags: List[str]


class BaseNetworkService(BaseService):
    _path: ClassVar[str] = 'api/v1/networks/isolated'

    async def create(  # noqa: WPS211
        self,
        *,
        location_id: str,
        name: str,
        description: str,
        network_prefix: str,
        mask: int,
        wait: bool = False,
    ) -> Union[TaskIDWrap, NetworkEntity]:
        task_wrap: TaskIDWrap = await self._http_client.post(
            path=self.path,
            payload={
                'location_id': location_id,
                'name': name,
                'description': description,
                'network_prefix': network_prefix,
                'mask': mask,
            },
        )
        if wait:
            task = await self._wait_task_completion(TaskId.parse(task_wrap['task_id']))
            return await self._read(task_resource_id(task, TaskResourceType.network))
        return task_wrap

    async def get(self, network_id: NetworkId) -> NetworkEntity:
        return await self._read(network_id.value)

    async def list(self) -> List[NetworkEntity]:  # noqa: WPS125
        networks_resp = await self._http_client.get(self.path)
        return networks_resp['isolated_networks']

    async def update(
        self,
        network_id: NetworkId,
        *,
        name: str,
        description: str,
    ) -> Union[TaskIDWrap, NetworkEntity]:
        path = self._make_path(network_id.value)
        return await self._http_client.put(
            path=path,
            payload={
                'name': name,
                'description': description,
            },
        )

    async def delete(self, network_id: NetworkId, wait: bool = False) -> Optional[TaskIDWrap]:
        path = with_return_task(self._make_path(network_id.value))
        task_wrap: TaskIDWrap = await self._http_client.delete(path)
        if wait:
            await self._wait_task_completion(self._task_id(task_wrap))
            return None
        return task_wrap

    async def _read(self, raw_network_id: str) -> NetworkEntity:
        network_resp = await self._http_client.get(self._make_path(raw_network_id))
        return network_resp['isolated_network']


class NetworkService(BaseNetworkService):
    def tags(self, network_id: NetworkId) -> TagService:
        return TagService(self._http_client, network_id)
