from enum import Enum, unique
from types import MappingProxyType
from typing import FrozenSet, List, Mapping, Type, TypedDict, Union


@unique
class AllowedTTLType(Enum):
    one_s = '1s'
    five_s = '5s'
    thirty_s = '30s'
    one_m = '1m'
    five_m = '5m'
    ten_m = '10m'
    fifteen = '15m'
    thirty_m = '30m'
    one_h = '1h'
    two_h = '2h'
    six_h = '6h'
    twelve = '12h'
    one_day = '1d'

    @classmethod
    def list(cls) -> List[str]:
        return [enum_item.value for enum_item in cls]


@unique
class AllowedRecordType(Enum):
    a = 'a'  # noqa: WPS111
    aaaa = 'aaaa'
    cname = 'cname'
    mx = 'mx'
    ns = 'ns'
    srv = 'srv'
    txt = 'txt'

    @classmethod
    def list(cls) -> List[str]:
        return [enum_item.value for enum_item in cls]


class BaseRecordEntity(TypedDict):
    """Общая часть записи, как её отдаёт publisher.

    `type` и `ttl` в теле — значения `AllowedRecordType` и `AllowedTTLType`:
    запись приходит документом JSON, и разбирать её обратно в enum незачем.
    """

    name: str
    type: str
    ttl: str


class ARecordEntity(BaseRecordEntity):
    ip: str


class AAAARecordEntity(BaseRecordEntity):
    ip: str


class CNAMERecordEntity(BaseRecordEntity):
    canonical_name: str


class MXRecordEntity(BaseRecordEntity):
    mail_host: str
    priority: int


class NSRecordEntity(BaseRecordEntity):
    name_server_host: str


class SRVRecordEntity(BaseRecordEntity):
    protocol: str
    service: str
    priority: int
    weight: int
    port: int
    target: str


class TXTRecordEntity(BaseRecordEntity):
    text: str


AnyRecord = Union[
    BaseRecordEntity,
    ARecordEntity,
    AAAARecordEntity,
    CNAMERecordEntity,
    MXRecordEntity,
    NSRecordEntity,
    SRVRecordEntity,
    TXTRecordEntity,
]

# Значение поля записи в теле запроса: строка адреса, имени или текста —
# либо число приоритета, веса и порта.
RecordFieldValue = Union[str, int]

_ENTITY_BY_RECORD_TYPE: Mapping[AllowedRecordType, Type[BaseRecordEntity]] = MappingProxyType({
    AllowedRecordType.a: ARecordEntity,
    AllowedRecordType.aaaa: AAAARecordEntity,
    AllowedRecordType.cname: CNAMERecordEntity,
    AllowedRecordType.mx: MXRecordEntity,
    AllowedRecordType.ns: NSRecordEntity,
    AllowedRecordType.srv: SRVRecordEntity,
    AllowedRecordType.txt: TXTRecordEntity,
})

BASE_RECORD_FIELDS: FrozenSet[str] = frozenset(BaseRecordEntity.__required_keys__)


def record_type_fields(record_type: AllowedRecordType) -> FrozenSet[str]:
    """Поля записи данного типа сверх общих `name`, `type` и `ttl`."""
    return frozenset(_ENTITY_BY_RECORD_TYPE[record_type].__required_keys__) - BASE_RECORD_FIELDS
