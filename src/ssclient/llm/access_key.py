from typing import ClassVar, List, Optional, Sequence, Union

from ssclient.base import BaseService, Payload, TaskIDWrap, with_filters
from ssclient.llm.entities import LlmAccessKeyEntity, LlmAccessKeySecretEntity
from ssclient.llm.ids import LlmAccessKeyId, LlmGroupId
from ssclient.task_entities import TaskResourceType, task_resource_id

_GROUP_KEYS_PATH = 'api/v1/llm/groups/{group_id}/access-keys'


class LlmAccessKeyService(BaseService):
    _path: ClassVar[str] = 'api/v1/llm/access-keys'

    async def list(self, group_id: Optional[LlmGroupId] = None) -> List[LlmAccessKeyEntity]:
        keys_resp = await self._http_client.get(with_filters(self.path, {'group_id': group_id}))
        return keys_resp['access_keys']

    async def get(self, group_id: LlmGroupId, access_key_id: LlmAccessKeyId) -> LlmAccessKeyEntity:
        key_resp = await self._http_client.get(_key_path(group_id, access_key_id))
        return key_resp['access_key']

    async def issue(
        self, group_id: LlmGroupId, *, name: str, wait: bool = False,
    ) -> Union[TaskIDWrap, LlmAccessKeyEntity]:
        task_wrap: TaskIDWrap = await self._http_client.post(
            path=_GROUP_KEYS_PATH.format(group_id=group_id),
            payload={'name': name},
        )
        if wait:
            task = await self._wait_task_completion(self._task_id(task_wrap))
            raw_key_id = task_resource_id(task, TaskResourceType.llm_access_key)
            return await self.get(group_id, LlmAccessKeyId(int(raw_key_id)))
        return task_wrap

    async def reveal_secret(
        self, group_id: LlmGroupId, access_key_id: LlmAccessKeyId,
    ) -> LlmAccessKeySecretEntity:
        return await self._http_client.post(
            path=_key_path(group_id, access_key_id, 'secret'),
            payload=None,
        )

    async def lock(
        self,
        group_id: LlmGroupId,
        access_key_id: LlmAccessKeyId,
        *,
        reason: Optional[str] = None,
        wait: bool = False,
    ) -> Union[TaskIDWrap, LlmAccessKeyEntity]:
        payload: Payload = {}
        if reason is not None:
            payload['reason'] = reason
        task_wrap: TaskIDWrap = await self._http_client.post(
            path=_key_path(group_id, access_key_id, 'lock'),
            payload=payload,
        )
        return await self._key_after_task(group_id, access_key_id, task_wrap, wait=wait)

    async def unlock(
        self, group_id: LlmGroupId, access_key_id: LlmAccessKeyId, *, wait: bool = False,
    ) -> Union[TaskIDWrap, LlmAccessKeyEntity]:
        task_wrap: TaskIDWrap = await self._http_client.post(
            path=_key_path(group_id, access_key_id, 'unlock'),
            payload=None,
        )
        return await self._key_after_task(group_id, access_key_id, task_wrap, wait=wait)

    async def delete(
        self, group_id: LlmGroupId, access_key_id: LlmAccessKeyId, wait: bool = False,
    ) -> Optional[TaskIDWrap]:
        task_wrap: TaskIDWrap = await self._http_client.delete(_key_path(group_id, access_key_id))
        if wait:
            await self._wait_task_completion(self._task_id(task_wrap))
            return None
        return task_wrap

    async def set_tags(
        self, group_id: LlmGroupId, access_key_id: LlmAccessKeyId, *, tags: Sequence[str],
    ) -> None:
        await self._http_client.put(
            path=_key_path(group_id, access_key_id, 'tags'),
            payload={'tags': list(tags)},
        )

    async def _key_after_task(
        self,
        group_id: LlmGroupId,
        access_key_id: LlmAccessKeyId,
        task_wrap: TaskIDWrap,
        *,
        wait: bool,
    ) -> Union[TaskIDWrap, LlmAccessKeyEntity]:
        if not wait:
            return task_wrap
        await self._wait_task_completion(self._task_id(task_wrap))
        return await self.get(group_id, access_key_id)


def _key_path(group_id: LlmGroupId, access_key_id: LlmAccessKeyId, fragment: str = '') -> str:
    path = '{keys_path}/{access_key_id}'.format(
        keys_path=_GROUP_KEYS_PATH.format(group_id=group_id), access_key_id=access_key_id,
    )
    if not fragment:
        return path
    return '{path}/{fragment}'.format(path=path, fragment=fragment)
