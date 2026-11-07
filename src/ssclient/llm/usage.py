import datetime
from dataclasses import dataclass
from typing import ClassVar, Optional

from ssclient.base import BaseService, with_filters
from ssclient.llm.entities import LlmRequestLogEntity, LlmUsageEntity, LlmUsageGroupBy
from ssclient.llm.ids import LlmAccessKeyId, LlmGroupId, LlmModelId


@dataclass(frozen=True)
class LlmUsageQuery(object):
    """Запрос расхода: период обязателен, обе даты включительно; разрез и фильтры — по выбору."""

    period_from: datetime.date
    period_to: datetime.date
    group_by: Optional[LlmUsageGroupBy] = None
    group_id: Optional[LlmGroupId] = None
    access_key_id: Optional[LlmAccessKeyId] = None
    model_id: Optional[LlmModelId] = None


class LlmUsageService(BaseService):
    _path: ClassVar[str] = 'api/v1/llm/'

    async def usage(self, query: LlmUsageQuery) -> LlmUsageEntity:
        path = with_filters(self._make_path('usage'), {
            'from': query.period_from.isoformat(),
            'to': query.period_to.isoformat(),
            'group_by': query.group_by.value if query.group_by else None,
            'group_id': query.group_id,
            'access_key_id': query.access_key_id,
            'model_id': query.model_id,
        })
        usage_resp = await self._http_client.get(path)
        return usage_resp['usage']

    async def requests(self) -> LlmRequestLogEntity:
        return await self._http_client.get(self._make_path('requests'))
