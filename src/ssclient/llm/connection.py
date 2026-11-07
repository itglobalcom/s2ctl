from typing import ClassVar, Union

from ssclient.base import BaseService, TaskIDWrap
from ssclient.llm.entities import LlmConnectionEntity


class LlmConnectionService(BaseService):
    _path: ClassVar[str] = 'api/v1/llm/connection'

    async def get(self) -> LlmConnectionEntity:
        connection_resp = await self._http_client.get(self.path)
        return connection_resp['connection']

    async def connect(
        self, *, group_name: str, first_key_name: str, wait: bool = False,
    ) -> Union[TaskIDWrap, LlmConnectionEntity]:
        task_wrap: TaskIDWrap = await self._http_client.post(
            path=self.path,
            payload={
                'group_name': group_name,
                'first_key_name': first_key_name,
            },
        )
        if wait:
            await self._wait_task_completion(self._task_id(task_wrap))
            return await self.get()
        return task_wrap
