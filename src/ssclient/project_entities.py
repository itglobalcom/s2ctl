from typing import List, NotRequired, TypedDict


class ServiceConsumptionEntity(TypedDict):
    service: str
    total: float


class ResourceConsumptionEntity(TypedDict):
    service: str
    type: str
    id: NotRequired[str]
    name: NotRequired[str]
    total: float


class DayConsumptionEntity(TypedDict):
    date: str
    total: float


ConsumptionEntity = TypedDict('ConsumptionEntity', {
    'from': str,
    'to': str,
    'time_zone': str,
    'currency': str,
    'is_final': bool,
    'total': float,
})


class ProjectConsumptionEntity(ConsumptionEntity):
    services: List[ServiceConsumptionEntity]


class ProjectConsumptionResourcesEntity(ConsumptionEntity):
    resources: List[ResourceConsumptionEntity]


class ProjectConsumptionDailyEntity(ConsumptionEntity):
    days: List[DayConsumptionEntity]
