from typing import ClassVar, List, TypedDict, Union

from ssclient.base import BaseService, TaskIDWrap
from ssclient.domain.record import RecordService
from ssclient.domain.record_entities import AnyRecord

DOMAIN_CREATION_TIMEOUT = 60 * 3  # 3 min


class DomainEntity(TypedDict):
    name: str
    is_delegated: bool
    records: List[AnyRecord]


class BaseDomainService(BaseService):
    _path: ClassVar[str] = 'api/v1/domains/'

    async def create(
        self,
        *,
        name: str,
        migrate_records: bool = False,
        wait: bool = False,
    ) -> Union[TaskIDWrap, DomainEntity]:
        task_wrap: TaskIDWrap = await self._http_client.post(
            path=self.path,
            payload={
                'name': name,
                'migrate_records': migrate_records,
            },
        )
        if wait:
            task = await self._wait_task_completion(task_wrap['task_id'], DOMAIN_CREATION_TIMEOUT)
            return await self.get(task['domain_id'])
        return task_wrap

    async def get(self, domain_name: str) -> DomainEntity:
        path = self._make_path(domain_name)
        domain_resp = await self._http_client.get(path)
        return domain_resp['domain']

    async def list(self) -> List[DomainEntity]:  # noqa: WPS125
        domains_resp = await self._http_client.get(self.path)
        return domains_resp['domains']

    async def delete(self, domain_name: str) -> None:
        path = self._make_path(domain_name)
        await self._http_client.delete(path)


class DomainService(BaseDomainService):
    def records(self, domain_name: str) -> RecordService:
        return RecordService(self._http_client, domain_name)
