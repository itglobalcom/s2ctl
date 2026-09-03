import asyncio
from typing import ClassVar, List, NamedTuple, Optional, Sequence, TypedDict, Union

from ssclient.base import BaseService, Payload, TaskIDWrap, with_filters
from ssclient.task_entities import TaskResourceType, task_resource_id
from ssclient.task_id import TaskId
from ssclient.vmware.edge import VmwareEdgeService
from ssclient.vmware.ids import VmwareLocationId, VmwareNetworkId, VmwareServerId


class VmwareNetworkEntity(TypedDict):
    id: int  # noqa: WPS125
    location_id: int
    type: str  # noqa: WPS125
    name: str
    address: str
    mask: int
    gateway: str
    bandwidth_mbps: int
    is_dhcp: bool
    shared: bool
    state: str
    nics_count: int


class TaskIDsWrap(TypedDict):
    task_ids: List[str]


class VmwareServerNic(NamedTuple):
    """Сервер, подключаемый к сети, и адрес, который получит его интерфейс."""

    server_id: VmwareServerId
    ip: Optional[str] = None


def _create_payload(location_id: VmwareLocationId, name: str) -> Payload:
    """Общая часть запроса создания: локацию и имя требует любой из трёх типов сети."""
    return {'location_id': location_id, 'name': name}


class BaseVmwareNetworkService(BaseService):
    _path: ClassVar[str] = 'api/v1/vmware/networks'

    async def list(  # noqa: WPS125
        self,
        location_id: Optional[VmwareLocationId] = None,
        network_type: Optional[str] = None,
    ) -> List[VmwareNetworkEntity]:
        path = with_filters(self.path, {'location_id': location_id, 'type': network_type})
        networks_resp = await self._http_client.get(path)
        return networks_resp['networks']

    async def get(self, network_id: VmwareNetworkId) -> VmwareNetworkEntity:
        network_resp = await self._http_client.get(self._network_path(network_id))
        return network_resp['network']

    async def rename(
        self, network_id: VmwareNetworkId, *, name: str, wait: bool = False,
    ) -> Union[TaskIDWrap, VmwareNetworkEntity, None]:
        return await self._edit(network_id, {'name': name}, wait=wait)

    async def set_bandwidth(
        self, network_id: VmwareNetworkId, *, bandwidth_mbps: int, wait: bool = False,
    ) -> Union[TaskIDWrap, VmwareNetworkEntity, None]:
        return await self._edit(network_id, {'bandwidth_mbps': bandwidth_mbps}, wait=wait)

    async def delete(self, network_id: VmwareNetworkId, wait: bool = False) -> Optional[TaskIDWrap]:
        # Удаление VMware-сети отдаёт ссылку на задачу само, без `return_task=true`.
        task_wrap: TaskIDWrap = await self._http_client.delete(self._network_path(network_id))
        if wait:
            await self._wait_task_completion(self._task_id(task_wrap))
            return None
        return task_wrap

    async def _edit(
        self, network_id: VmwareNetworkId, payload: Payload, *, wait: bool,
    ) -> Union[TaskIDWrap, VmwareNetworkEntity, None]:
        # Правку изолированной сети publisher применяет синхронно и отвечает 204 без задачи.
        task_wrap: Optional[TaskIDWrap] = await self._http_client.put(
            path=self._network_path(network_id),
            payload=payload,
        )
        if not wait:
            return task_wrap
        if task_wrap:
            await self._wait_task_completion(self._task_id(task_wrap))
        return await self.get(network_id)

    def _network_path(self, network_id: VmwareNetworkId, fragment: str = '') -> str:
        path = self._make_path(str(network_id))
        if not fragment:
            return path
        return '{path}/{fragment}'.format(path=path, fragment=fragment)


class VmwareNetworkService(BaseVmwareNetworkService):
    # WPS211: состав параметров задан формой запроса контракта — операция неделима.
    async def create_isolated(  # noqa: WPS211
        self,
        *,
        location_id: VmwareLocationId,
        name: str,
        address: str,
        mask: Optional[int] = None,
        enable_dhcp: bool = False,
        wait: bool = False,
    ) -> Union[TaskIDWrap, VmwareNetworkEntity]:
        payload = _create_payload(location_id, name)
        payload.update({'address': address, 'mask': mask, 'enable_dhcp': enable_dhcp})
        return await self._create('isolated', payload, wait=wait)

    # WPS211: состав параметров задан формой запроса контракта — операция неделима.
    async def create_routed(  # noqa: WPS211
        self,
        *,
        location_id: VmwareLocationId,
        name: str,
        address: str,
        mask: Optional[int] = None,
        enable_dhcp: bool = False,
        bandwidth_mbps: Optional[int] = None,
        wait: bool = False,
    ) -> Union[TaskIDWrap, VmwareNetworkEntity]:
        payload = _create_payload(location_id, name)
        payload.update({
            'address': address,
            'mask': mask,
            'enable_dhcp': enable_dhcp,
            'bandwidth_mbps': bandwidth_mbps,
        })
        return await self._create('routed', payload, wait=wait)

    async def create_public(
        self,
        *,
        location_id: VmwareLocationId,
        name: str,
        capacity: str,
        bandwidth_mbps: Optional[int] = None,
        wait: bool = False,
    ) -> Union[TaskIDWrap, VmwareNetworkEntity]:
        payload = _create_payload(location_id, name)
        payload.update({'capacity': capacity, 'bandwidth_mbps': bandwidth_mbps})
        return await self._create('public', payload, wait=wait)

    async def connect_servers(
        self,
        network_id: VmwareNetworkId,
        *,
        nics: Sequence[VmwareServerNic],
        force_customization: bool = False,
        wait: bool = False,
    ) -> Union[TaskIDsWrap, VmwareNetworkEntity]:
        tasks_wrap: TaskIDsWrap = await self._http_client.post(
            path=self._network_path(network_id, 'servers'),
            payload={
                'nics': [{'server_id': nic.server_id, 'ip': nic.ip} for nic in nics],
                'force_customization': force_customization,
            },
        )
        if not wait:
            return tasks_wrap

        # Publisher порождает отдельную задачу на каждый подключаемый сервер.
        await asyncio.gather(*[
            self._wait_task_completion(TaskId.parse(raw_task_id))
            for raw_task_id in tasks_wrap['task_ids']
        ])
        return await self.get(network_id)

    def edge(self, network_id: VmwareNetworkId) -> VmwareEdgeService:
        return VmwareEdgeService(self._http_client, network_id)

    async def _create(
        self, network_kind: str, payload: Payload, *, wait: bool,
    ) -> Union[TaskIDWrap, VmwareNetworkEntity]:
        task_wrap: TaskIDWrap = await self._http_client.post(
            path=self._make_path(network_kind),
            payload=payload,
        )
        if not wait:
            return task_wrap

        task = await self._wait_task_completion(self._task_id(task_wrap))
        return await self.get(VmwareNetworkId(int(task_resource_id(task, TaskResourceType.network))))
