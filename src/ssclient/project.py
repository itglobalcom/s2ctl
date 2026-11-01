import datetime
from typing import Any, ClassVar, Dict, Optional, TypedDict

from ssclient.base import BaseService, with_filters
from ssclient.project_entities import (
    ProjectConsumptionDailyEntity,
    ProjectConsumptionEntity,
    ProjectConsumptionResourcesEntity,
)

_CONSUMPTION = 'consumption'


class ProjectEntity(TypedDict):
    id: str
    balance: float
    currency: str
    state: str
    created: str


class ProjectService(BaseService):
    _path: ClassVar[str] = 'api/v1/project'

    async def get(self) -> ProjectEntity:
        project_resp = await self._http_client.get(self.path)
        return project_resp['project']

    async def consumption(
        self,
        period_from: Optional[datetime.date] = None,
        period_to: Optional[datetime.date] = None,
    ) -> ProjectConsumptionEntity:
        return await self._consumption(_CONSUMPTION, _period(period_from, period_to))

    async def consumption_resources(
        self,
        period_from: Optional[datetime.date] = None,
        period_to: Optional[datetime.date] = None,
        service: Optional[str] = None,
    ) -> ProjectConsumptionResourcesEntity:
        filters = {**_period(period_from, period_to), 'service': service}
        return await self._consumption('{path}/resources'.format(path=_CONSUMPTION), filters)

    async def consumption_daily(
        self,
        period_from: Optional[datetime.date] = None,
        period_to: Optional[datetime.date] = None,
    ) -> ProjectConsumptionDailyEntity:
        return await self._consumption('{path}/daily'.format(path=_CONSUMPTION), _period(period_from, period_to))

    async def _consumption(self, fragment: str, filters: Dict[str, Optional[str]]) -> Any:
        consumption_resp = await self._http_client.get(with_filters(self._make_path(fragment), filters))
        return consumption_resp[_CONSUMPTION]


def _period(
    period_from: Optional[datetime.date], period_to: Optional[datetime.date],
) -> Dict[str, Optional[str]]:
    return {
        'from': period_from.isoformat() if period_from else None,
        'to': period_to.isoformat() if period_to else None,
    }
