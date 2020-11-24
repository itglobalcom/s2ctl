from typing import ClassVar, Optional

from ssclient.base import BaseService, TaskIDWrap
from ssclient.ports import HttpClientPort


class ServerPowerService(BaseService):
    _path: ClassVar[str] = 'api/v1/servers/{server_id}/power'

    def __init__(self, http_client: HttpClientPort, server_id: str) -> None:
        super().__init__(http_client, {'server_id': server_id})

    async def power_on(self, wait: bool = False) -> Optional[TaskIDWrap]:
        path = self._make_path('on')
        task_wrap: TaskIDWrap = await self._http_client.post(
            path=path,
            payload={},
        )
        if wait:
            task_id = self._extrac_task_id(task_wrap)
            await self._wait_task_completion(task_id)
            return None
        return task_wrap

    async def power_off(self, wait: bool = False) -> Optional[TaskIDWrap]:
        path = self._make_path('off')
        task_wrap: TaskIDWrap = await self._http_client.post(
            path=path,
            payload={},
        )
        if wait:
            task_id = self._extrac_task_id(task_wrap)
            await self._wait_task_completion(task_id)
            return None
        return task_wrap

    async def shutdown(self, wait: bool = False) -> Optional[TaskIDWrap]:
        path = self._make_path('shutdown')
        task_wrap: TaskIDWrap = await self._http_client.post(
            path=path,
            payload={},
        )
        if wait:
            task_id = self._extrac_task_id(task_wrap)
            await self._wait_task_completion(task_id)
            return None
        return task_wrap

    async def reboot(self, wait: bool = False) -> Optional[TaskIDWrap]:
        path = self._make_path('reboot')
        task_wrap: TaskIDWrap = await self._http_client.post(
            path=path,
            payload={},
        )
        if wait:
            task_id = self._extrac_task_id(task_wrap)
            await self._wait_task_completion(task_id)
            return None
        return task_wrap

    async def reset(self, wait: bool = False) -> Optional[TaskIDWrap]:
        path = self._make_path('reset')
        task_wrap: TaskIDWrap = await self._http_client.post(
            path=path,
            payload={},
        )
        if wait:
            await self._wait_task_completion(task_wrap['task_id'])
            return None
        return task_wrap

    def _extrac_task_id(self, task_wrap: TaskIDWrap) -> str:
        return task_wrap['task_id']
