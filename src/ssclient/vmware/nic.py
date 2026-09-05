from typing import ClassVar, List, Optional, Union

from ssclient.base import BaseService, Payload, TaskIDWrap
from ssclient.ports import HttpClientPort
from ssclient.vmware.ids import VmwareNetworkId, VmwareNicId, VmwareServerId
from ssclient.vmware.server_entities import VmwareServerNicEntity

_SHARED_FRAGMENT = 'shared'


class VmwareServerNicService(BaseService):
    """Интерфейсы VMware-сервера.

    Подключение к клиентской сети и к общей — разные операции контракта с разной
    формой запроса: у клиентской сети задаётся сеть и адрес, у общей — полоса.
    """

    _path: ClassVar[str] = 'api/v1/vmware/servers/{server_id}/nics'

    def __init__(self, http_client: HttpClientPort, server_id: VmwareServerId) -> None:
        super().__init__(http_client, {'server_id': server_id})

    async def list(self) -> List[VmwareServerNicEntity]:
        nics_resp = await self._http_client.get(self.path)
        return nics_resp['nics']

    async def connect_client_network(
        self,
        *,
        network_id: VmwareNetworkId,
        ip: Optional[str] = None,
        force_customization: bool = False,
        wait: bool = False,
    ) -> Union[TaskIDWrap, List[VmwareServerNicEntity]]:
        return await self._connect(
            self.path,
            {
                'network_id': network_id,
                'ip': ip,
                'force_customization': force_customization,
            },
            wait=wait,
        )

    async def connect_shared_network(
        self, *, bandwidth_mbps: int, force_customization: bool = False, wait: bool = False,
    ) -> Union[TaskIDWrap, List[VmwareServerNicEntity]]:
        # Общая сеть всегда IPv4: выбора адресной семьи контракт не предлагает.
        return await self._connect(
            self._make_path(_SHARED_FRAGMENT),
            {
                'bandwidth_mbps': bandwidth_mbps,
                'force_customization': force_customization,
            },
            wait=wait,
        )

    async def update(
        self,
        nic_id: VmwareNicId,
        *,
        network_id: VmwareNetworkId,
        bandwidth_mbps: Optional[int] = None,
        ip: Optional[str] = None,
        force_customization: bool = False,
        wait: bool = False,
    ) -> Union[TaskIDWrap, List[VmwareServerNicEntity]]:
        task_wrap: TaskIDWrap = await self._http_client.put(
            path=self._make_path(str(nic_id)),
            payload={
                'network_id': network_id,
                'bandwidth_mbps': bandwidth_mbps,
                'ip': ip,
                'force_customization': force_customization,
            },
        )
        if not wait:
            return task_wrap
        await self._wait_task_completion(self._task_id(task_wrap))
        # Чтения одного интерфейса в контракте нет — только набор интерфейсов сервера.
        return await self.list()

    async def disconnect(self, nic_id: VmwareNicId, wait: bool = False) -> Optional[TaskIDWrap]:
        # Отключение интерфейса VMware отдаёт ссылку на задачу само, без `return_task=true`.
        task_wrap: TaskIDWrap = await self._http_client.delete(self._make_path(str(nic_id)))
        if wait:
            await self._wait_task_completion(self._task_id(task_wrap))
            return None
        return task_wrap

    async def _connect(
        self, path: str, payload: Payload, *, wait: bool,
    ) -> Union[TaskIDWrap, List[VmwareServerNicEntity]]:
        task_wrap: TaskIDWrap = await self._http_client.post(path=path, payload=payload)
        if not wait:
            return task_wrap
        await self._wait_task_completion(self._task_id(task_wrap))
        # Ни ответ операции, ни `resources[]` VMware-задачи не несут id созданного
        # интерфейса: задача публикует ресурсы только двух типов, server и network.
        return await self.list()
