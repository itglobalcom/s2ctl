from typing import ClassVar, List, Optional, Sequence, TypedDict

from ssclient.base import BaseService, TaskIDWrap
from ssclient.gateway.gateway_id import GatewayId
from ssclient.ports import HttpClientPort


class NatRuleEntity(TypedDict):
    type: str  # noqa: WPS125
    protocol: str
    source: str
    destination: str
    destination_port: int
    translated: str
    translated_port: int


class NatService(BaseService):
    _path: ClassVar[str] = 'api/v1/gateways/{gateway_id}/nat'

    def __init__(self, http_client: HttpClientPort, gateway_id: GatewayId) -> None:
        super().__init__(http_client, {'gateway_id': gateway_id.value})

    async def get(self) -> List[NatRuleEntity]:
        rules_resp = await self._http_client.get(self.path)
        return rules_resp['nat_rules']

    async def replace(
        self, rules: Sequence[NatRuleEntity], wait: bool = False,
    ) -> Optional[TaskIDWrap]:
        task_wrap: TaskIDWrap = await self._http_client.put(
            path=self.path,
            payload={
                'nat_rules': list(rules),
            },
        )
        if wait:
            await self._wait_task_completion(self._task_id(task_wrap))
            return None
        return task_wrap
