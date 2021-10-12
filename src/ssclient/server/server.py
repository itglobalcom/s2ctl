from dataclasses import asdict, dataclass
from typing import Iterable, List, Optional, TypedDict, Union

from ssclient.base import BaseService, TaskIDWrap
from ssclient.server.nic import NicService
from ssclient.server.power import ServerPowerService
from ssclient.server.snapshot import SnapshotService
from ssclient.server.tag import TagService
from ssclient.server.volume import VolumeService


class ServerVolumeEntity(TypedDict):
    id: int  # noqa: WPS125
    name: str
    size_mb: int
    created: str


class ServerNicEntity(TypedDict):
    id: int  # noqa: WPS125
    network_id: str
    mac: str
    ip_address: str
    mask: int
    bandwidth_mbps: int


class ServerEntity(TypedDict):
    id: str  # noqa: WPS125
    location_id: str
    cpu: int
    ram_mb: int
    volumes: List[ServerVolumeEntity]
    nics: List[ServerNicEntity]
    image_id: str
    is_power_on: bool
    name: str
    login: str
    password: str
    ssh_key_ids: List[int]
    state: str
    created: str
    tags: List[str]


@dataclass
class VolumeCreationData(object):
    name: str
    size_mb: int


class BaseServerService(BaseService):
    _path = 'api/v1/servers'

    async def create(  # noqa: WPS211
        self,
        *,
        name: str,
        location_id: str,
        image_id: str,
        cpu: int,
        ram_mb: int,
        volumes: Iterable[VolumeCreationData],
        networks: Iterable[int],
        ssh_key_ids: List[int],
        wait: bool = False,
    ) -> Union[TaskIDWrap, ServerEntity]:
        task_wrap: TaskIDWrap = await self._http_client.post(
            path=self.path,
            payload={
                'name': name,
                'location_id': location_id,
                'image_id': image_id,
                'cpu': cpu,
                'ram_mb': ram_mb,
                'volumes': [asdict(disk) for disk in volumes],
                'networks': [{'bandwidth_mbps': bandwidth} for bandwidth in networks],
                'ssh_key_ids': ssh_key_ids,
            },
        )
        if wait:
            task = await self._wait_task_completion(task_wrap['task_id'])
            return await self.get(task['server_id'])
        return task_wrap

    async def get(self, server_id: str) -> ServerEntity:
        path = self._make_path(server_id)

        server_resp = await self._http_client.get(path)
        return server_resp['server']

    async def list(self) -> List[ServerEntity]:  # noqa: WPS125
        servers_resp = await self._http_client.get(self.path)
        return servers_resp['servers']

    async def update(
        self,
        server_id: str,
        *,
        cpu: Optional[int] = None,
        ram_mb: Optional[int] = None,
        wait: bool = True,
    ) -> Union[TaskIDWrap, ServerEntity]:
        path = self._make_path(server_id)

        payload = {}
        if cpu is not None:
            payload['cpu'] = cpu

        if ram_mb is not None:
            payload['ram_mb'] = ram_mb

        task_wrap: TaskIDWrap = await self._http_client.patch(
            path=path,
            payload=payload,
        )
        if wait:
            task = await self._wait_task_completion(task_wrap['task_id'])
            return await self.get(task['server_id'])
        return task_wrap

    async def delete(self, server_id: str) -> None:
        path = self._make_path(server_id)
        await self._http_client.delete(path)


class ServerService(BaseServerService):
    def power(self, server_id: str) -> ServerPowerService:
        return ServerPowerService(self._http_client, server_id)

    def volumes(self, server_id: str) -> VolumeService:
        return VolumeService(self._http_client, server_id)

    def snapshots(self, server_id: str) -> SnapshotService:
        return SnapshotService(self._http_client, server_id)

    def nics(self, server_id: str) -> NicService:
        return NicService(self._http_client, server_id)

    def tags(self, server_id: str) -> TagService:
        return TagService(self._http_client, server_id)
