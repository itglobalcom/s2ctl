from enum import Enum, unique
from typing import List, NotRequired, TypedDict


class BackupRuleEntity(TypedDict):
    keep: int
    backup_storage_id: int


@unique
class Weekday(Enum):
    """День недели еженедельного правила; закрытый словарь контракта."""

    monday = 'monday'
    tuesday = 'tuesday'
    wednesday = 'wednesday'
    thursday = 'thursday'
    friday = 'friday'
    saturday = 'saturday'
    sunday = 'sunday'


class BackupWeeklyRuleEntity(BackupRuleEntity):
    weekday: str


class BackupMonthlyRuleEntity(BackupRuleEntity):
    day_of_month: str


class BackupScheduleEntity(TypedDict):
    """Расписание копий: отсутствующее правило выключено."""

    hour: int
    minute: int
    daily: NotRequired[BackupRuleEntity]
    weekly: NotRequired[BackupWeeklyRuleEntity]
    monthly: NotRequired[BackupMonthlyRuleEntity]


class ServerBackupEntity(TypedDict):
    enabled: bool
    schedule: NotRequired[BackupScheduleEntity]


class BackupRuleLimitsEntity(TypedDict):
    max_keep: int
    default_keep: int


class BackupLimitsEntity(TypedDict):
    schedule_window_from_hour: int
    schedule_window_to_hour: int
    daily: BackupRuleLimitsEntity
    weekly: BackupRuleLimitsEntity
    monthly: BackupRuleLimitsEntity


class BackupStorageEntity(TypedDict):
    id: int
    name: NotRequired[str]
    description: NotRequired[str]
    sort_order: int
    price_per_gb: float
    location_id: str
    restore_location_ids: List[str]


class BackupStoragesEntity(TypedDict):
    storages: List[BackupStorageEntity]
    limits: BackupLimitsEntity


@unique
class RestorePointState(Enum):
    """Состояние точки восстановления; закрытый словарь контракта."""

    in_progress = 'in_progress'
    active = 'active'
    failed = 'failed'


class RestorePointEntity(TypedDict):
    id: int
    server_id: str
    name: NotRequired[str]
    size_mb: int
    backup_storage_id: NotRequired[int]
    state: str
    created: NotRequired[str]
    retained_by: List[str]
    keep_until: NotRequired[str]
    is_manual: bool
