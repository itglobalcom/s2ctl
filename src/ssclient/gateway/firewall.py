from typing import ClassVar, List, Optional, Sequence, TypedDict

from ssclient.base import BaseService, TaskIDWrap
from ssclient.gateway.gateway_id import GatewayId
from ssclient.ports import HttpClientPort


class FirewallRuleEntity(TypedDict):
    action: str
    direction: str
    protocol: str
    source: str
    source_port: int
    destination: str
    destination_port: int


class FirewallService(BaseService):
    _path: ClassVar[str] = 'api/v1/gateways/{gateway_id}/firewall'

    def __init__(self, http_client: HttpClientPort, gateway_id: GatewayId) -> None:
        super().__init__(http_client, {'gateway_id': gateway_id.value})

    async def get(self) -> List[FirewallRuleEntity]:
        rules_resp = await self._http_client.get(self.path)
        return rules_resp['firewall_rules']

    async def replace(
        self, rules: Sequence[FirewallRuleEntity], wait: bool = False,
    ) -> Optional[TaskIDWrap]:
        task_wrap: TaskIDWrap = await self._http_client.put(
            path=self.path,
            payload={
                'firewall_rules': list(rules),
            },
        )
        if wait:
            await self._wait_task_completion(self._task_id(task_wrap))
            return None
        return task_wrap
