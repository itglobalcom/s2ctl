from typing import ClassVar, List, Sequence, Union

from ssclient.base import BaseService, TaskIDWrap
from ssclient.llm.entities import LlmGroupDetailsEntity, LlmGroupEntity
from ssclient.llm.ids import LlmGroupId, LlmModelId
from ssclient.task_entities import TaskResourceType, task_resource_id


class LlmGroupService(BaseService):
    _path: ClassVar[str] = 'api/v1/llm/groups'

    async def list(self) -> List[LlmGroupEntity]:
        groups_resp = await self._http_client.get(self.path)
        return groups_resp['groups']

    async def get(self, group_id: LlmGroupId) -> LlmGroupDetailsEntity:
        group_resp = await self._http_client.get(_group_path(self.path, group_id))
        return group_resp['group']

    async def create(self, *, name: str, wait: bool = False) -> Union[TaskIDWrap, LlmGroupDetailsEntity]:
        task_wrap: TaskIDWrap = await self._http_client.post(path=self.path, payload={'name': name})
        if wait:
            task = await self._wait_task_completion(self._task_id(task_wrap))
            return await self.get(LlmGroupId(int(task_resource_id(task, TaskResourceType.llm_group))))
        return task_wrap

    async def set_models(
        self, group_id: LlmGroupId, *, model_ids: Sequence[LlmModelId], wait: bool = False,
    ) -> Union[TaskIDWrap, LlmGroupDetailsEntity]:
        task_wrap: TaskIDWrap = await self._http_client.put(
            path=_group_path(self.path, group_id, 'models'),
            payload={'model_ids': list(model_ids)},
        )
        return await self._group_after_task(group_id, task_wrap, wait=wait)

    async def set_tags(self, group_id: LlmGroupId, *, tags: Sequence[str]) -> None:
        await self._http_client.put(
            path=_group_path(self.path, group_id, 'tags'),
            payload={'tags': list(tags)},
        )

    async def disable(
        self, group_id: LlmGroupId, *, wait: bool = False,
    ) -> Union[TaskIDWrap, LlmGroupDetailsEntity]:
        task_wrap: TaskIDWrap = await self._http_client.post(
            path=_group_path(self.path, group_id, 'disable'),
            payload=None,
        )
        return await self._group_after_task(group_id, task_wrap, wait=wait)

    async def _group_after_task(
        self, group_id: LlmGroupId, task_wrap: TaskIDWrap, *, wait: bool,
    ) -> Union[TaskIDWrap, LlmGroupDetailsEntity]:
        if not wait:
            return task_wrap
        await self._wait_task_completion(self._task_id(task_wrap))
        return await self.get(group_id)


def _group_path(groups_path: str, group_id: LlmGroupId, fragment: str = '') -> str:
    path = '{groups_path}/{group_id}'.format(groups_path=groups_path, group_id=group_id)
    if not fragment:
        return path
    return '{path}/{fragment}'.format(path=path, fragment=fragment)
