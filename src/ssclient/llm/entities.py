from enum import Enum, unique
from typing import List, NotRequired, TypedDict


@unique
class LlmUsageGroupBy(Enum):
    """Разрез расхода; publisher отдаёт и принимает его строкой в snake_case."""

    none = 'none'
    day = 'day'
    model = 'model'
    group = 'group'
    access_key = 'access_key'


class LlmConnectionEntity(TypedDict):
    state: str
    task_id: NotRequired[str]
    group_name: NotRequired[str]
    first_key_name: NotRequired[str]


class LlmSpendAmountEntity(TypedDict):
    credits: float
    cost: NotRequired[float]


class LlmCreditPriceEntity(TypedDict):
    basis: str
    price_per_credit: float
    currency: str
    tax_label: NotRequired[str]
    package_name: NotRequired[str]
    valid_through: NotRequired[str]


class LlmGroupModelEntity(TypedDict):
    model_id: int
    tech_title: str
    name: str
    pending_operation: NotRequired[str]


class LlmGroupEntity(TypedDict):
    """Группа проекта; группа в создании — только имя, время создания и задача."""

    name: str
    created_at: str
    id: NotRequired[int]
    state: NotRequired[str]
    tags: NotRequired[List[str]]
    models: NotRequired[List[LlmGroupModelEntity]]
    pending_operation: NotRequired[str]
    is_read_only: NotRequired[bool]
    task_id: NotRequired[str]


class LlmGroupSpendPeriodsEntity(TypedDict):
    today: LlmSpendAmountEntity
    week: LlmSpendAmountEntity
    month: LlmSpendAmountEntity


class LlmGroupDetailsEntity(LlmGroupEntity):
    deployment_state: str
    spend: LlmGroupSpendPeriodsEntity
    total_spent_credits: int
    updated_at: str


class LlmAccessKeyLocksEntity(TypedDict):
    by_client: bool
    by_quota: bool
    by_admin: bool
    by_balance: bool
    by_platform: bool
    client_reason: NotRequired[str]


class LlmAccessKeyEntity(TypedDict):
    """Ключ доступа; ключ в выпуске — группа, имя, время создания и задача."""

    group_id: int
    name: str
    created_at: str
    id: NotRequired[int]
    group_name: NotRequired[str]
    state: NotRequired[str]
    locks: NotRequired[LlmAccessKeyLocksEntity]
    tags: NotRequired[List[str]]
    consumed_credits: NotRequired[int]
    month_spend: NotRequired[LlmSpendAmountEntity]
    expires_at: NotRequired[str]
    last_used_at: NotRequired[str]
    is_secret_available: NotRequired[bool]
    pending_operation: NotRequired[str]
    is_group_read_only: NotRequired[bool]
    task_id: NotRequired[str]


class LlmAccessKeySecretEntity(TypedDict):
    secret: str


class LlmModelStartingPriceEntity(TypedDict):
    provider: str
    input: float
    is_from_live_provider: bool
    output: NotRequired[float]


class LlmModelPriceEntity(TypedDict):
    unit: str
    credits: float
    variant: NotRequired[str]
    money: NotRequired[float]


class LlmModelEntity(TypedDict):
    id: int
    tech_title: str
    name: str
    description: str
    vendor: str
    kind: str
    contour: str
    storage_countries: List[str]
    is_pii_protected: bool
    context_size: int
    unit_kind: str
    endpoint: str
    is_available_to_groups: bool
    starting_price: NotRequired[LlmModelStartingPriceEntity]
    prices_collected_at: NotRequired[str]


class LlmModelCatalogEntity(TypedDict):
    models: List[LlmModelEntity]
    credit_price: NotRequired[LlmCreditPriceEntity]
    prices_collected_at: NotRequired[str]


class LlmModelProviderEntity(TypedDict):
    slug: str
    name: str
    prices: List[LlmModelPriceEntity]
    discount: float
    is_live: bool
    supports_tools: bool
    supports_reasoning: bool
    supports_structured_outputs: bool
    supports_web_search: bool
    variant: NotRequired[str]
    context_length: NotRequired[int]
    max_completion_tokens: NotRequired[int]


class LlmModelProtectedPriceEntity(TypedDict):
    model: List[LlmModelPriceEntity]
    recognition: LlmModelPriceEntity
    total: List[LlmModelPriceEntity]


class LlmModelDetailsEntity(LlmModelEntity):
    default_provider: str
    prices: List[LlmModelPriceEntity]
    providers: List[LlmModelProviderEntity]
    credit_price: NotRequired[LlmCreditPriceEntity]
    protected_price: NotRequired[LlmModelProtectedPriceEntity]
    supports_streaming: NotRequired[bool]
    supports_tools: NotRequired[bool]


class LlmPackageEntity(TypedDict):
    id: int
    tech_title: str
    volume_credits: int
    discount_percent: float
    price: float
    period_from: str
    period_to: str
    auto_renew: bool
    state: str
    full_month_volume_credits: NotRequired[int]
    full_month_price: NotRequired[float]


class LlmPackageUsageEntity(TypedDict):
    period_from: str
    period_to: str
    total_credits: float
    in_package_credits: float
    over_package_credits: float
    package_volume_credits: NotRequired[int]


class LlmPackageStopEntity(TypedDict):
    stopped_at: str
    reason: str
    state: str


class LlmCurrentPackageEntity(TypedDict):
    usage: LlmPackageUsageEntity
    currency: str
    packages_disabled: bool
    exhausted_package_mode: str
    package: NotRequired[LlmPackageEntity]
    price_per_credit: NotRequired[float]
    tax_label: NotRequired[str]
    pay_as_you_go_limit_credits: NotRequired[int]
    stop: NotRequired[LlmPackageStopEntity]


class LlmPackagePlanMonthTermsEntity(TypedDict):
    period_from: str
    period_to: str
    volume_credits: int
    price: float


class LlmPackagePlanEntity(TypedDict):
    id: int
    tech_title: str
    description: str
    volume_credits: int
    discount_percent: float
    price: float
    currency: str
    tax_label: NotRequired[str]
    current_month: NotRequired[LlmPackagePlanMonthTermsEntity]


class LlmUsageAmountsEntity(TypedDict):
    credits: float
    local_credits: float
    external_credits: float
    in_tokens: int
    out_tokens: int
    cached_tokens: int
    cost: NotRequired[float]


class LlmUsageItemEntity(LlmUsageAmountsEntity):
    """Строка расхода: кроме сумм — только поля своего разреза."""

    date: NotRequired[str]
    model_id: NotRequired[int]
    model_tech_title: NotRequired[str]
    model_name: NotRequired[str]
    group_id: NotRequired[int]
    group_name: NotRequired[str]
    access_key_id: NotRequired[int]
    access_key_name: NotRequired[str]


class LlmUsageCollectionEntity(TypedDict):
    state: str
    collected_at: NotRequired[str]
    attempted_at: NotRequired[str]


# Ключи `from` и `items` — имена полей контракта: `from` в синтаксисе класса недопустим.
LlmUsageEntity = TypedDict('LlmUsageEntity', {
    'from': str,
    'to': str,
    'group_by': str,
    'totals': LlmUsageAmountsEntity,
    'items': List[LlmUsageItemEntity],
    'collection': LlmUsageCollectionEntity,
    'credit_price': NotRequired[LlmCreditPriceEntity],
})


class LlmRequestLogItemEntity(TypedDict):
    occurred_at: str
    group_id: int
    access_key_id: int
    model_tech_title: str
    response_code: int
    duration_ms: int
    in_tokens: int
    out_tokens: int
    cached_tokens: int
    credits: float
    model_id: NotRequired[int]


class LlmRequestLogEntity(TypedDict):
    source_connected: bool
    requests: List[LlmRequestLogItemEntity]
