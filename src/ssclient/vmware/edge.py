from typing import ClassVar, List, Optional, Sequence, Union

from ssclient.base import BaseService, TaskIDWrap
from ssclient.ports import HttpClientPort
from ssclient.vmware.ids import VmwareNatRuleId, VmwareNetworkId, VmwareVpnTunnelId
from ssclient.vmware.edge_entities import (
    VmwareEdgeFirewallEntity,
    VmwareEdgeFirewallRuleEntity,
    VmwareEdgeNatRuleEntity,
    VmwareEdgeVpnEntity,
)

EDGE_PATH = 'api/v1/vmware/networks/{network_id}/edge'

_NETWORK_ID_FIELD = 'network_id'


class BaseEdgeService(BaseService):
    def __init__(self, http_client: HttpClientPort, network_id: VmwareNetworkId) -> None:
        super().__init__(http_client, {_NETWORK_ID_FIELD: network_id})
        self._network_id = network_id


class VmwareEdgeFirewallService(BaseEdgeService):
    _path: ClassVar[str] = '{edge_path}/firewall'.format(edge_path=EDGE_PATH)

    async def get(self) -> VmwareEdgeFirewallEntity:
        firewall_resp = await self._http_client.get(self.path)
        return firewall_resp['firewall']

    async def update(
        self,
        *,
        rules: Sequence[VmwareEdgeFirewallRuleEntity],
        enabled: Optional[bool] = None,
        default_action: Optional[str] = None,
        wait: bool = False,
    ) -> Union[TaskIDWrap, VmwareEdgeFirewallEntity, None]:
        # Набор правил заменяется целиком; не переданные `enabled` и `default_action`
        # publisher оставляет в текущем значении, поэтому их отсутствие — не «выключить».
        task_wrap: Optional[TaskIDWrap] = await self._http_client.put(
            path=self.path,
            payload={
                'enabled': enabled,
                'default_action': default_action,
                'rules': list(rules),
            },
        )
        if not wait:
            return task_wrap
        if task_wrap:
            await self._wait_task_completion(self._task_id(task_wrap))
        return await self.get()


class VmwareEdgeNatService(BaseEdgeService):
    _path: ClassVar[str] = '{edge_path}/nat'.format(edge_path=EDGE_PATH)

    async def get(self) -> List[VmwareEdgeNatRuleEntity]:
        nat_resp = await self._http_client.get(self.path)
        return nat_resp['rules']

    # WPS211: состав параметров задан формой запроса контракта — операция неделима.
    async def upsert_rule(  # noqa: WPS211
        self,
        *,
        rule_type: str,
        protocol: str,
        original_ip: str,
        translated_ip: str,
        rule_id: Optional[VmwareNatRuleId] = None,
        original_port: Optional[str] = None,
        translated_port: Optional[str] = None,
        description: Optional[str] = None,
        enabled: Optional[bool] = None,
        wait: bool = False,
    ) -> Union[TaskIDWrap, List[VmwareEdgeNatRuleEntity]]:
        # Правило задаётся целиком: `rule_id` выбирает изменяемое, без него правило создаётся.
        task_wrap: TaskIDWrap = await self._http_client.post(
            path=self.path,
            payload={
                'rule_id': rule_id,
                'type': rule_type,
                'description': description,
                'protocol': protocol,
                'original_ip': original_ip,
                'original_port': original_port,
                'translated_ip': translated_ip,
                'translated_port': translated_port,
                'enabled': enabled,
            },
        )
        if not wait:
            return task_wrap

        await self._wait_task_completion(self._task_id(task_wrap))
        return await self.get()

    async def delete_rule(self, rule_id: VmwareNatRuleId, wait: bool = False) -> Optional[TaskIDWrap]:
        task_wrap: TaskIDWrap = await self._http_client.delete(self._make_path(str(rule_id)))
        if wait:
            await self._wait_task_completion(self._task_id(task_wrap))
            return None
        return task_wrap


class VmwareEdgeVpnService(BaseEdgeService):
    _path: ClassVar[str] = '{edge_path}/vpn'.format(edge_path=EDGE_PATH)

    async def get(self) -> VmwareEdgeVpnEntity:
        vpn_resp = await self._http_client.get(self.path)
        return vpn_resp['vpn']

    # WPS211: состав параметров задан формой запроса контракта — операция неделима.
    async def upsert_tunnel(  # noqa: WPS211
        self,
        *,
        name: str,
        shared_key: str,
        peer_network: str,
        peer_endpoint: str,
        peer_identificator: str,
        mtu: int,
        encryption_type: str,
        diffie_hellman_group: str,
        tunnel_id: Optional[VmwareVpnTunnelId] = None,
        enabled: Optional[bool] = None,
        perfect_forward_secrecy: Optional[bool] = None,
        wait: bool = False,
    ) -> Union[TaskIDWrap, VmwareEdgeVpnEntity]:
        # Туннель задаётся целиком: `tunnel_id` выбирает изменяемый, без него туннель создаётся.
        task_wrap: TaskIDWrap = await self._http_client.post(
            path=self.path,
            payload={
                'tunnel_id': tunnel_id,
                'name': name,
                'enabled': enabled,
                'mtu': mtu,
                'encryption_type': encryption_type,
                'shared_key': shared_key,
                'peer_network': peer_network,
                'peer_endpoint': peer_endpoint,
                'peer_identificator': peer_identificator,
                'perfect_forward_secrecy': perfect_forward_secrecy,
                'diffie_hellman_group': diffie_hellman_group,
            },
        )
        if not wait:
            return task_wrap

        await self._wait_task_completion(self._task_id(task_wrap))
        return await self.get()

    async def delete_tunnel(self, tunnel_id: VmwareVpnTunnelId, wait: bool = False) -> Optional[TaskIDWrap]:
        task_wrap: TaskIDWrap = await self._http_client.delete(self._make_path(str(tunnel_id)))
        if wait:
            await self._wait_task_completion(self._task_id(task_wrap))
            return None
        return task_wrap


class VmwareEdgeService(BaseEdgeService):
    _path: ClassVar[str] = EDGE_PATH

    async def set_bandwidth(self, *, bandwidth_mbps: int, wait: bool = False) -> Optional[TaskIDWrap]:
        task_wrap: TaskIDWrap = await self._http_client.put(
            path=self._make_path('bandwidth'),
            payload={
                'bandwidth_mbps': bandwidth_mbps,
            },
        )
        if wait:
            await self._wait_task_completion(self._task_id(task_wrap))
            return None
        return task_wrap

    def firewall(self) -> VmwareEdgeFirewallService:
        return VmwareEdgeFirewallService(self._http_client, self._network_id)

    def nat(self) -> VmwareEdgeNatService:
        return VmwareEdgeNatService(self._http_client, self._network_id)

    def vpn(self) -> VmwareEdgeVpnService:
        return VmwareEdgeVpnService(self._http_client, self._network_id)
