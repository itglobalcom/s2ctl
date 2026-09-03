from dataclasses import asdict
from typing import Any, ClassVar, Dict, List, Optional, TypedDict, Union

from ssclient.base import BaseService, Payload, TaskIDWrap, with_filters
from ssclient.task_id import TaskId
from ssclient.vmware.firewall import VmwareServerFirewallService
from ssclient.vmware.nic import VmwareServerNicService
from ssclient.vmware.power import VmwareServerPowerService
from ssclient.vmware.server_entities import (
    VmwareServerEntity,
    VmwareServerOrder,
    VmwareServerOrderRef,
)
from ssclient.vmware.snapshot import VmwareServerSnapshotService
from ssclient.vmware.volume import VmwareServerVolumeService

_NESTED_HYPERVISOR_PATH = 'nested-hypervisor/{transition}'


class VmwareNestedHypervisorRef(TypedDict):
    """Ответ переключателя вложенной виртуализации: у идемпотентного исхода задачи нет."""

    task_id: Optional[str]


class BaseVmwareServerService(BaseService):  # noqa: WPS214
    """Сервер VMware. WPS214: число методов задано составом операций раздела контракта."""

    _path: ClassVar[str] = 'api/v1/vmware/servers'

    async def list(self, location_id: Optional[int] = None) -> List[VmwareServerEntity]:  # noqa: WPS125
        path = with_filters(self.path, {'location_id': location_id})
        servers_resp = await self._http_client.get(path)
        return servers_resp['servers']

    async def get(self, server_id: int) -> VmwareServerEntity:
        server_resp = await self._http_client.get(self._server_path(server_id))
        return server_resp['server']

    async def create(
        self, order: VmwareServerOrder, wait: bool = False,
    ) -> Union[VmwareServerOrderRef, VmwareServerEntity]:
        return await self._order(self.path, _order_payload(order), wait=wait)

    async def verify(self, order: VmwareServerOrder) -> None:
        """Предпроверка заказа: сервер не создаётся, успех — пустой ответ."""
        await self._http_client.post(
            path=self._make_path('verify'),
            payload=_order_payload(order),
        )

    async def set_configuration(
        self,
        server_id: int,
        *,
        cpu: int,
        ram_mb: int,
        system_disk_size_mb: int,
        wait: bool = False,
    ) -> Union[TaskIDWrap, VmwareServerEntity]:
        task_wrap: TaskIDWrap = await self._http_client.put(
            path=self._server_path(server_id),
            payload={
                'cpu': cpu,
                'ram_mb': ram_mb,
                'system_disk_size_mb': system_disk_size_mb,
            },
        )
        return await self._task_result(task_wrap, server_id, wait=wait)

    async def rename(self, server_id: int, *, name: str) -> None:
        """Переименование применяется синхронно: publisher не заводит задачу и не отдаёт тела."""
        await self._http_client.put(
            path=self._server_path(server_id, 'name'),
            payload={'name': name},
        )

    async def set_computer_name(
        self,
        server_id: int,
        *,
        computer_name: str,
        force_customization: bool = False,
        wait: bool = False,
    ) -> Union[TaskIDWrap, VmwareServerEntity]:
        task_wrap: TaskIDWrap = await self._http_client.put(
            path=self._server_path(server_id, 'computer-name'),
            payload={
                'computer_name': computer_name,
                'force_customization': force_customization,
            },
        )
        return await self._task_result(task_wrap, server_id, wait=wait)

    async def copy(
        self,
        server_id: int,
        *,
        name: str,
        client_network_id: Optional[int] = None,
        wait: bool = False,
    ) -> Union[VmwareServerOrderRef, VmwareServerEntity]:
        return await self._order(
            self._server_path(server_id, 'copy'),
            {'name': name, 'client_network_id': client_network_id},
            wait=wait,
        )

    async def rebuild(
        self,
        server_id: int,
        *,
        image_id: int,
        need_sysprep: Optional[bool] = None,
        wait: bool = False,
    ) -> Union[VmwareServerOrderRef, VmwareServerEntity]:
        # Переустановка создаёт новый сервер с новым id, исходный уходит в удаление.
        return await self._order(
            self._server_path(server_id, 'rebuild'),
            {'image_id': image_id, 'need_sysprep': need_sysprep},
            wait=wait,
        )

    async def delete(self, server_id: int, wait: bool = False) -> Optional[TaskIDWrap]:
        # Удаление VMware-сервера отдаёт ссылку на задачу само, без `return_task=true`.
        task_wrap: TaskIDWrap = await self._http_client.delete(self._server_path(server_id))
        if wait:
            await self._wait_task_completion(self._task_id(task_wrap))
            return None
        return task_wrap

    async def enable_nested_hypervisor(
        self, server_id: int, wait: bool = False,
    ) -> Union[VmwareNestedHypervisorRef, VmwareServerEntity]:
        return await self._switch_nested_hypervisor(server_id, 'enable', wait=wait)

    async def disable_nested_hypervisor(
        self, server_id: int, wait: bool = False,
    ) -> Union[VmwareNestedHypervisorRef, VmwareServerEntity]:
        return await self._switch_nested_hypervisor(server_id, 'disable', wait=wait)

    async def _switch_nested_hypervisor(
        self, server_id: int, transition: str, *, wait: bool,
    ) -> Union[VmwareNestedHypervisorRef, VmwareServerEntity]:
        task_ref: VmwareNestedHypervisorRef = await self._http_client.post(
            path=self._server_path(
                server_id,
                _NESTED_HYPERVISOR_PATH.format(transition=transition),
            ),
            payload={},
        )
        if not wait:
            return task_ref
        # Вложенная виртуализация уже в требуемом состоянии — задачи нет, ждать нечего.
        raw_task_id = task_ref['task_id']
        if raw_task_id:
            await self._wait_task_completion(TaskId.parse(raw_task_id))
        return await self.get(server_id)

    async def _order(
        self, path: str, payload: Payload, *, wait: bool,
    ) -> Union[VmwareServerOrderRef, VmwareServerEntity]:
        # Заказ отдаёт id созданного сервера рядом с id задачи, поэтому ресурсы задачи
        # для его поиска не нужны: у copy и rebuild это id новой машины, а не исходной.
        order_ref: VmwareServerOrderRef = await self._http_client.post(path=path, payload=payload)
        if not wait:
            return order_ref
        await self._wait_task_completion(TaskId.parse(order_ref['task_id']))
        return await self.get(order_ref['server_id'])

    async def _task_result(
        self, task_wrap: TaskIDWrap, server_id: int, *, wait: bool,
    ) -> Union[TaskIDWrap, VmwareServerEntity]:
        if not wait:
            return task_wrap
        await self._wait_task_completion(self._task_id(task_wrap))
        return await self.get(server_id)

    def _server_path(self, server_id: int, fragment: str = '') -> str:
        path = self._make_path(str(server_id))
        if not fragment:
            return path
        return '{path}/{fragment}'.format(path=path, fragment=fragment)


class VmwareServerService(BaseVmwareServerService):
    def power(self, server_id: int) -> VmwareServerPowerService:
        return VmwareServerPowerService(self._http_client, server_id)

    def firewall(self, server_id: int) -> VmwareServerFirewallService:
        return VmwareServerFirewallService(self._http_client, server_id)

    def volumes(self, server_id: int) -> VmwareServerVolumeService:
        return VmwareServerVolumeService(self._http_client, server_id)

    def nics(self, server_id: int) -> VmwareServerNicService:
        return VmwareServerNicService(self._http_client, server_id)

    def snapshot(self, server_id: int) -> VmwareServerSnapshotService:
        return VmwareServerSnapshotService(self._http_client, server_id)


def _order_payload(order: VmwareServerOrder) -> Dict[str, Any]:
    payload = asdict(order)
    payload['ssh_keys'] = list(order.ssh_keys)
    return payload
