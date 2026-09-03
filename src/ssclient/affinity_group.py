import re
from typing import ClassVar, List, NamedTuple, Optional, TypedDict

from ssclient.base import BaseService, TaskIDWrap, with_return_task
from ssclient.task_id import TaskId

AFFINITY_GROUP_ID_TEMPLATE = 'l<location>g<group>'

_ID_PATTERN = re.compile(r'^l\d+g\d+$')


class AffinityGroupId(NamedTuple):
    """Составной id группы: так publisher адресует её в маршрутах чтения и удаления."""

    value: str  # noqa: WPS110

    @classmethod
    def try_parse(cls, raw_id: str) -> Optional['AffinityGroupId']:
        if _ID_PATTERN.match(raw_id):
            return cls(raw_id)
        return None


class AffinityGroupEntity(TypedDict):
    id: str  # noqa: WPS125
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

    async def list(self) -> List[AffinityGroupEntity]:  # noqa: WPS125
        groups_resp = await self._http_client.get(self.path)
        return groups_resp['affinity_groups']

    async def delete(self, group_id: AffinityGroupId, wait: bool = False) -> None:
        path = self._make_path(group_id.value)
        if not wait:
            await self._http_client.delete(path)
            return

        task_wrap: TaskIDWrap = await self._http_client.delete(with_return_task(path))
        await self._wait_task_completion(TaskId.parse(task_wrap['task_id']))
