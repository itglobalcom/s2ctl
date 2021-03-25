from typing import ClassVar, List, Optional, Union  # noqa: WPS226

from ssclient.base import BaseService, TaskIDWrap
from ssclient.domain import record_entities as entities
from ssclient.ports import HttpClientPort


class RecordService(BaseService):  # noqa: WPS214
    _path: ClassVar[str] = 'api/v1/domains/{domain_name}/records/'

    def __init__(self, http_client: HttpClientPort, domain_name: str) -> None:
        super().__init__(http_client, {'domain_name': domain_name})

    async def create_a(
        self,
        *,
        name: str,
        ttl: entities.AllowedTTLType,
        ip: str,
        wait: bool = False,
    ) -> Union[TaskIDWrap, entities.ARecordEntity]:
        return await self._craete_record(
            name=name,
            record_type=entities.AllowedRecordType.a,
            ttl=ttl,
            ip=ip,
            wait=wait,
        )  # type: ignore

    async def create_aaaa(
        self,
        *,
        name: str,
        ttl: entities.AllowedTTLType,
        ip: str,
        wait: bool = False,
    ) -> Union[TaskIDWrap, entities.ARecordEntity]:
        return await self._craete_record(
            name=name,
            record_type=entities.AllowedRecordType.aaaa,
            ttl=ttl,
            ip=ip,
            wait=wait,
        )  # type: ignore

    async def create_cname(
        self,
        *,
        name: str,
        ttl: entities.AllowedTTLType,
        canonical_name: str,
        wait: bool = False,
    ) -> Union[TaskIDWrap, entities.CNAMERecordEntity]:
        return await self._craete_record(
            name=name,
            record_type=entities.AllowedRecordType.cname,
            ttl=ttl,
            canonical_name=canonical_name,
            wait=wait,
        )  # type: ignore

    async def create_mx(
        self,
        *,
        name: str,
        ttl: entities.AllowedTTLType,
        mail_host: str,
        priority: int,
        wait: bool = False,
    ) -> Union[TaskIDWrap, entities.MXRecordEntity]:
        return await self._craete_record(
            name=name,
            record_type=entities.AllowedRecordType.mx,
            ttl=ttl,
            mail_host=mail_host,
            priority=priority,
            wait=wait,
        )  # type: ignore

    async def create_ns(
        self,
        *,
        name: str,
        ttl: entities.AllowedTTLType,
        name_server_host: str,
        wait: bool = False,
    ) -> Union[TaskIDWrap, entities.NSRecordEntity]:
        return await self._craete_record(
            name=name,
            record_type=entities.AllowedRecordType.ns,
            ttl=ttl,
            name_server_host=name_server_host,
            wait=wait,
        )  # type: ignore

    async def create_srv(  # noqa: WPS211
        self,
        *,
        name: str,
        ttl: entities.AllowedTTLType,
        protocol: str,
        service: str,
        priority: int,
        weight: int,
        port: int,
        target: str,
        wait: bool = False,
    ) -> Union[TaskIDWrap, entities.SRVRecordEntity]:
        return await self._craete_record(
            name=name,
            record_type=entities.AllowedRecordType.srv,
            ttl=ttl,
            protocol=protocol,
            service=service,
            priority=priority,
            weight=weight,
            port=port,
            target=target,
            wait=wait,
        )  # type: ignore

    async def create_txt(
        self,
        *,
        name: str,
        ttl: entities.AllowedTTLType,
        text: str,
        wait: bool = False,
    ) -> Union[TaskIDWrap, entities.NSRecordEntity]:
        return await self._craete_record(
            name=name,
            record_type=entities.AllowedRecordType.txt,
            ttl=ttl,
            text=text,
            wait=wait,
        )  # type: ignore

    async def get(self, record_id: int) -> entities.AnyRecord:
        path = self._make_path(str(record_id))
        record_resp = await self._http_client.get(path)
        return record_resp['record']

    async def list(self) -> List[entities.AnyRecord]:  # noqa: WPS125
        domains_resp = await self._http_client.get(self.path)
        return domains_resp['records']

    async def update(  # noqa: WPS211
        self,
        record_id: int,
        *,
        name: str,
        ttl: entities.AllowedTTLType,
        record_type: entities.AllowedRecordType,
        ip: Optional[str] = None,
        cname: Optional[str] = None,
        mail_host: Optional[str] = None,
        name_server_host: Optional[str] = None,
        text: Optional[str] = None,
        protocol: Optional[str] = None,
        service: Optional[str] = None,
        weight: Optional[int] = None,
        port: Optional[int] = None,
        target: Optional[str] = None,
        priority: Optional[int] = None,
        wait: bool = False,
    ) -> Union[TaskIDWrap, entities.AnyRecord]:
        path = self._make_path(str(record_id))
        payload = {
            'name': name,
            'type': record_type.value,
            'ttl': ttl.value,
        }
        if ip:
            payload['ip'] = ip
        if cname:
            payload['canonical_name'] = cname
        if mail_host:
            payload['mail_host'] = mail_host
        if name_server_host:
            payload['name_server_host'] = name_server_host
        if text:
            payload['text'] = text
        if protocol:
            payload['protocol'] = protocol
        if service:
            payload['service'] = service
        if weight:
            payload['weight'] = weight
        if port:
            payload['port'] = port
        if target:
            payload['target'] = target
        if priority:
            payload['priority'] = priority
        task_wrap: TaskIDWrap = await self._http_client.put(
            path=path,
            payload=payload,
        )
        if wait:
            task = await self._wait_task_completion(task_wrap['task_id'])
            return await self.get(task['record_id'])
        return task_wrap

    async def delete(self, record_id: int) -> None:
        path = self._make_path(str(record_id))
        await self._http_client.delete(path)

    async def _craete_record(
        self,
        name: str,
        record_type: entities.AllowedRecordType,
        ttl: entities.AllowedTTLType,
        wait: bool = False,
        **other_fields,
    ) -> Union[TaskIDWrap, entities.AnyRecord]:
        task_wrap: TaskIDWrap = await self._http_client.post(
            path=self.path,
            payload={
                'name': name,
                'type': record_type.value,
                'ttl': ttl.value,
                **other_fields,
            },
        )
        if wait:
            task = await self._wait_task_completion(task_wrap['task_id'])
            return await self.get(task['record_id'])
        return task_wrap
