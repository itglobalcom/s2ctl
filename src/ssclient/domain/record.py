from typing import Any, ClassVar, Dict, List, Mapping, Optional, Union

from ssclient.base import BaseService, TaskIDWrap, with_return_task
from ssclient.domain import record_entities as entities
from ssclient.ports import HttpClientPort
from ssclient.task_entities import TaskResourceType, task_resource_id

RecordFields = Mapping[str, entities.RecordFieldValue]


def _record_payload(
    *,
    name: str,
    record_type: entities.AllowedRecordType,
    ttl: entities.AllowedTTLType,
    fields: RecordFields,
) -> Dict[str, Any]:
    return {
        'name': name,
        'type': record_type.value,
        'ttl': ttl.value,
        **fields,
    }


class RecordService(BaseService):
    _path: ClassVar[str] = 'api/v1/domains/{domain_name}/records/'

    def __init__(self, http_client: HttpClientPort, domain_name: str) -> None:
        super().__init__(http_client, {'domain_name': domain_name})

    async def create(
        self,
        *,
        name: str,
        record_type: entities.AllowedRecordType,
        ttl: entities.AllowedTTLType,
        fields: RecordFields,
        wait: bool = False,
    ) -> Union[TaskIDWrap, entities.AnyRecord]:
        """Создаёт запись: состав `fields` задаёт тип записи."""
        task_wrap: TaskIDWrap = await self._http_client.post(
            path=self.path,
            payload=_record_payload(name=name, record_type=record_type, ttl=ttl, fields=fields),
        )
        return await self._created_record(task_wrap, wait=wait)

    async def update(
        self,
        record_id: int,
        *,
        name: str,
        record_type: entities.AllowedRecordType,
        ttl: entities.AllowedTTLType,
        fields: RecordFields,
        wait: bool = False,
    ) -> Union[TaskIDWrap, entities.AnyRecord]:
        """Заменяет запись целиком: publisher принимает тело того же состава, что и создание."""
        task_wrap: TaskIDWrap = await self._http_client.put(
            path=self._make_path(str(record_id)),
            payload=_record_payload(name=name, record_type=record_type, ttl=ttl, fields=fields),
        )
        return await self._created_record(task_wrap, wait=wait)

    async def get(self, record_id: int) -> entities.AnyRecord:
        path = self._make_path(str(record_id))
        record_resp = await self._http_client.get(path)
        return record_resp['record']

    async def list(self) -> List[entities.AnyRecord]:
        domains_resp = await self._http_client.get(self.path)
        return domains_resp['records']

    async def delete(self, record_id: int, wait: bool = False) -> Optional[TaskIDWrap]:
        path = with_return_task(self._make_path(str(record_id)))
        task_wrap: TaskIDWrap = await self._http_client.delete(path)
        if wait:
            await self._wait_task_completion(self._task_id(task_wrap))
            return None
        return task_wrap

    async def _created_record(
        self, task_wrap: TaskIDWrap, *, wait: bool,
    ) -> Union[TaskIDWrap, entities.AnyRecord]:
        if not wait:
            return task_wrap
        task = await self._wait_task_completion(self._task_id(task_wrap))
        return await self.get(int(task_resource_id(task, TaskResourceType.record)))
