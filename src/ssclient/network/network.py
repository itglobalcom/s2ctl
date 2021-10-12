from typing import ClassVar, List, TypedDict, Union

from ssclient.base import BaseService, TaskIDWrap
from ssclient.network.tag import TagService


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
            task = await self._wait_task_completion(task_wrap['task_id'])
            return await self.get(task['network_id'])
        return task_wrap

    async def get(self, network_id: str) -> NetworkEntity:
        path = self._make_path(network_id)
        network_resp = await self._http_client.get(path)
        return network_resp['isolated_network']

    async def list(self) -> List[NetworkEntity]:  # noqa: WPS125
        networks_resp = await self._http_client.get(self.path)
        return networks_resp['isolated_networks']

    async def update(
        self,
        network_id: str,
        *,
        name: str,
        description: str,
    ) -> Union[TaskIDWrap, NetworkEntity]:
        path = self._make_path(network_id)
        return await self._http_client.put(
            path=path,
            payload={
                'name': name,
                'description': description,
            },
        )

    async def delete(self, network_id: str) -> None:
        path = self._make_path(network_id)
        await self._http_client.delete(path)


class NetworkService(BaseNetworkService):
    def tags(self, network_id: str) -> TagService:
        return TagService(self._http_client, network_id)
