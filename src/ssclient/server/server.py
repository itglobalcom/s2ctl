from dataclasses import asdict, dataclass
from typing import Iterable, List, Optional, TypedDict, Union

from ssclient.base import BaseService, TaskIDWrap, with_return_task
from ssclient.server.nic import NicService
from ssclient.server.power import ServerPowerService
from ssclient.server.price import ServerPriceService
from ssclient.server.server_id import ServerId
from ssclient.server.snapshot import SnapshotService
from ssclient.server.tag import TagService
from ssclient.server.volume import VolumeService
from ssclient.task_entities import TaskResourceType, task_resource_id


class ServerVolumeEntity(TypedDict):
    id: int
    name: str
    size_mb: int
    created: str


class ServerNicEntity(TypedDict):
    id: int
    network_id: str
    mac: str
    ip_address: str
    mask: int
    bandwidth_mbps: int


class ServerEntity(TypedDict):
    id: str
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


# WPS214: число методов задано составом операций раздела контракта,
# а не сложностью класса.
class BaseServerService(BaseService):  # noqa: WPS214
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
            task = await self._wait_task_completion(self._task_id(task_wrap))
            return await self._read(task_resource_id(task, TaskResourceType.server))
        return task_wrap

    async def get(self, server_id: ServerId) -> ServerEntity:
        return await self._read(server_id.value)

    async def list(self) -> List[ServerEntity]:
        servers_resp = await self._http_client.get(self.path)
        return servers_resp['servers']

    async def update(
        self,
        server_id: ServerId,
        *,
        cpu: Optional[int] = None,
        ram_mb: Optional[int] = None,
        wait: bool = True,
    ) -> Union[TaskIDWrap, ServerEntity]:
        path = self._make_path(server_id.value)

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
            task = await self._wait_task_completion(self._task_id(task_wrap))
            return await self._read(task_resource_id(task, TaskResourceType.server))
        return task_wrap

    async def set_configuration(
        self,
        server_id: ServerId,
        *,
        cpu: int,
        ram_mb: int,
        wait: bool = False,
    ) -> Union[TaskIDWrap, ServerEntity]:
        path = self._make_path(server_id.value)

        task_wrap: TaskIDWrap = await self._http_client.put(
            path=path,
            payload={
                'cpu': cpu,
                'ram_mb': ram_mb,
            },
        )
        if wait:
            await self._wait_task_completion(self._task_id(task_wrap))
            return await self.get(server_id)
        return task_wrap

    async def rename(
        self, server_id: ServerId, *, name: str, wait: bool = False,
    ) -> Union[TaskIDWrap, ServerEntity]:
        path = '{server_path}/name'.format(server_path=self._make_path(server_id.value))

        task_wrap: TaskIDWrap = await self._http_client.put(
            path=path,
            payload={
                'name': name,
            },
        )
        if wait:
            await self._wait_task_completion(self._task_id(task_wrap))
            return await self.get(server_id)
        return task_wrap

    async def delete(self, server_id: ServerId, wait: bool = False) -> Optional[TaskIDWrap]:
        path = with_return_task(self._make_path(server_id.value))
        task_wrap: TaskIDWrap = await self._http_client.delete(path)
        if wait:
            await self._wait_task_completion(self._task_id(task_wrap))
            return None
        return task_wrap

    async def _read(self, raw_server_id: str) -> ServerEntity:
        server_resp = await self._http_client.get(self._make_path(raw_server_id))
        return server_resp['server']


class ServerService(BaseServerService):
    def prices(self) -> ServerPriceService:
        return ServerPriceService(self._http_client)

    def power(self, server_id: ServerId) -> ServerPowerService:
        return ServerPowerService(self._http_client, server_id)

    def volumes(self, server_id: ServerId) -> VolumeService:
        return VolumeService(self._http_client, server_id)

    def snapshots(self, server_id: ServerId) -> SnapshotService:
        return SnapshotService(self._http_client, server_id)

    def nics(self, server_id: ServerId) -> NicService:
        return NicService(self._http_client, server_id)

    def tags(self, server_id: ServerId) -> TagService:
        return TagService(self._http_client, server_id)
