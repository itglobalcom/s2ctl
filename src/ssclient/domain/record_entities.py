from enum import Enum, unique
from typing import Literal, Optional, Type, TypedDict, Union


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
    def list(cls):  # noqa: WPS125
        return [enum_item.value for enum_item in cls]


TTLType = Literal[AllowedTTLType.list()]


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
    def list(cls):  # noqa: WPS125
        return [enum_item.value for enum_item in cls]

    def __eq__(self, other):
        if isinstance(other, str):
            return self.value == other
        return super().__eq__(other)


RecordType = Literal[AllowedRecordType.list()]


class BaseRecordEntity(TypedDict):
    name: str
    type: RecordType  # noqa: WPS125
    ttl: TTLType


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


def get_record_entity_by_type(  # noqa: WPS212
    record_type: RecordType,
) -> Optional[Type[AnyRecord]]:
    if record_type == AllowedRecordType.a.value:
        return ARecordEntity
    if record_type == AllowedRecordType.aaaa.value:
        return AAAARecordEntity
    if record_type == AllowedRecordType.cname.value:
        return CNAMERecordEntity
    if record_type == AllowedRecordType.mx.value:
        return MXRecordEntity
    if record_type == AllowedRecordType.ns.value:
        return NSRecordEntity
    if record_type == AllowedRecordType.srv.value:
        return SRVRecordEntity
    if record_type == AllowedRecordType.txt.value:
        return TXTRecordEntity
    return None
