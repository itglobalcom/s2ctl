from typing import ClassVar, List, Optional, Sequence, TypedDict, Union

from ssclient.base import BaseService, TaskIDWrap, with_filters, with_return_task
from ssclient.gateway.firewall import FirewallRuleEntity, FirewallService
from ssclient.gateway.gateway_id import GatewayId
from ssclient.gateway.nat import NatRuleEntity, NatService
from ssclient.gateway.nic import GatewayNicEntity, GatewayNicService
from ssclient.gateway.power import GatewayPowerService
from ssclient.gateway.tag import TagService
from ssclient.network.network_id import NetworkId
from ssclient.task_entities import TaskResourceType, task_resource_id


class GatewayEntity(TypedDict):
    id: str
    location_id: str
    name: str
    nics: List[GatewayNicEntity]
    nat_rules: List[NatRuleEntity]
    firewall_rules: List[FirewallRuleEntity]
    state: str
    powered_on: bool
    created: str
    tags: List[str]


class BaseGatewayService(BaseService):
    _path: ClassVar[str] = 'api/v1/gateways'

    async def create(
        self,
        *,
        location_id: str,
        name: str,
        bandwidth_mbps: Optional[int],
        network_ids: Sequence[NetworkId],
        wait: bool = False,
    ) -> Union[TaskIDWrap, GatewayEntity]:
        task_wrap: TaskIDWrap = await self._http_client.post(
            path=self.path,
            payload={
                'location_id': location_id,
                'name': name,
                'bandwidth_mbps': bandwidth_mbps,
                'network_ids': [network_id.value for network_id in network_ids],
            },
        )
        if wait:
            task = await self._wait_task_completion(self._task_id(task_wrap))
            return await self._read(task_resource_id(task, TaskResourceType.gateway))
        return task_wrap

    async def get(self, gateway_id: GatewayId) -> GatewayEntity:
        return await self._read(gateway_id.value)

    async def list(self, location_id: Optional[str] = None) -> List[GatewayEntity]:
        path = with_filters(self.path, {'location_id': location_id})
        gateways_resp = await self._http_client.get(path)
        return gateways_resp['gateways']

    async def rename(self, gateway_id: GatewayId, *, name: str) -> GatewayEntity:
        gateway_resp = await self._http_client.put(
            path=self._make_path(gateway_id.value),
            payload={
                'name': name,
            },
        )
        return gateway_resp['gateway']

    async def set_bandwidth(
        self, gateway_id: GatewayId, *, bandwidth_mbps: int, wait: bool = False,
    ) -> Union[TaskIDWrap, GatewayEntity]:
        path = '{gateway_path}/bandwidth'.format(gateway_path=self._make_path(gateway_id.value))
        task_wrap: TaskIDWrap = await self._http_client.put(
            path=path,
            payload={
                'bandwidth_mbps': bandwidth_mbps,
            },
        )
        if wait:
            await self._wait_task_completion(self._task_id(task_wrap))
            return await self.get(gateway_id)
        return task_wrap

    async def delete(self, gateway_id: GatewayId, wait: bool = False) -> Optional[TaskIDWrap]:
        path = with_return_task(self._make_path(gateway_id.value))
        task_wrap: TaskIDWrap = await self._http_client.delete(path)
        if wait:
            await self._wait_task_completion(self._task_id(task_wrap))
            return None
        return task_wrap

    async def _read(self, raw_gateway_id: str) -> GatewayEntity:
        gateway_resp = await self._http_client.get(self._make_path(raw_gateway_id))
        return gateway_resp['gateway']


class GatewayService(BaseGatewayService):
    def firewall(self, gateway_id: GatewayId) -> FirewallService:
        return FirewallService(self._http_client, gateway_id)

    def nat(self, gateway_id: GatewayId) -> NatService:
        return NatService(self._http_client, gateway_id)

    def nics(self, gateway_id: GatewayId) -> GatewayNicService:
        return GatewayNicService(self._http_client, gateway_id)

    def power(self, gateway_id: GatewayId) -> GatewayPowerService:
        return GatewayPowerService(self._http_client, gateway_id)

    def tags(self, gateway_id: GatewayId) -> TagService:
        return TagService(self._http_client, gateway_id)
