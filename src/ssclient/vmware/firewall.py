from typing import ClassVar, List, Optional, Sequence, TypedDict, Union

from ssclient.base import BaseService, TaskIDWrap
from ssclient.ports import HttpClientPort
from ssclient.vmware.ids import VmwareServerId


class VmwareServerFirewallRuleEntity(TypedDict):
    name: str
    traffic_direction: str
    action: str
    protocol: str
    source: str
    source_port: str
    destination: str
    destination_port: str


class VmwareServerFirewallService(BaseService):
    """Межсетевой экран самой машины; экран на границе сети — это edge, другой раздел."""

    _path: ClassVar[str] = 'api/v1/vmware/servers/{server_id}/firewall'

    def __init__(self, http_client: HttpClientPort, server_id: VmwareServerId) -> None:
        super().__init__(http_client, {'server_id': server_id})

    async def get(self) -> List[VmwareServerFirewallRuleEntity]:
        firewall_resp = await self._http_client.get(self.path)
        return firewall_resp['rules']

    async def update(
        self, *, rules: Sequence[VmwareServerFirewallRuleEntity], wait: bool = False,
    ) -> Union[TaskIDWrap, List[VmwareServerFirewallRuleEntity], None]:
        # Набор правил заменяется целиком; правку без фактических изменений publisher
        # закрывает 204 без тела — задачи в таком ответе нет, ждать нечего.
        task_wrap: Optional[TaskIDWrap] = await self._http_client.put(
            path=self.path,
            payload={'rules': list(rules)},
        )
        if not wait:
            return task_wrap
        if task_wrap:
            await self._wait_task_completion(self._task_id(task_wrap))
        return await self.get()
