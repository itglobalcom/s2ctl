from typing import ClassVar, List, Optional, TypedDict

from ssclient.affinity_group_id import AffinityGroupId
from ssclient.base import BaseService, TaskIDWrap, with_filters, with_return_task


class AffinityGroupEntity(TypedDict):
    id: str
    location_id: str
    name: str
    affinity: bool
    server_ids: List[str]


class AffinityGroupService(BaseService):
    _path: ClassVar[str] = 'api/v1/affinity-groups'

    async def create(
        self, *, location_id: str, name: str, affinity: bool,
    ) -> AffinityGroupEntity:
        group_resp = await self._http_client.post(
            path=self.path,
            payload={
                'location_id': location_id,
                'name': name,
                'affinity': affinity,
            },
        )
        return group_resp['affinity_group']

    async def get(self, group_id: AffinityGroupId) -> AffinityGroupEntity:
        path = self._make_path(group_id.value)
        group_resp = await self._http_client.get(path)
        return group_resp['affinity_group']

    async def list(
        self, location_id: Optional[str] = None,
    ) -> List[AffinityGroupEntity]:
        path = with_filters(self.path, {'location_id': location_id})
        groups_resp = await self._http_client.get(path)
        return groups_resp['affinity_groups']

    async def delete(self, group_id: AffinityGroupId, wait: bool = False) -> Optional[TaskIDWrap]:
        # Удаление группы синхронное: ссылкой на задачу publisher отдаёт синтетический
        # `already_completed_task`, и ждать его нечем.
        path = with_return_task(self._make_path(group_id.value))
        task_wrap: TaskIDWrap = await self._http_client.delete(path)
        if wait:
            await self._wait_task_completion(self._task_id(task_wrap))
            return None
        return task_wrap
