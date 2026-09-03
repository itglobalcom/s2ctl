import re
from typing import NamedTuple, Optional

GATEWAY_ID_TEMPLATE = 'l<location>e<gateway>'

_ID_PATTERN = re.compile(r'^l\d+e\d+$')


class GatewayId(NamedTuple):
    """Составной id шлюза: так publisher адресует его в маршрутах раздела."""

    value: str  # noqa: WPS110

    @classmethod
    def try_parse(cls, raw_id: str) -> Optional['GatewayId']:
        if _ID_PATTERN.match(raw_id):
            return cls(raw_id)
        return None
