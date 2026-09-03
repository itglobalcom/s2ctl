import re
from typing import NamedTuple, Optional

NETWORK_ID_TEMPLATE = 'l<location>n<network>'

_ID_PATTERN = re.compile(r'^l\d+n\d+$')


class NetworkId(NamedTuple):
    """Составной id изолированной сети: так publisher адресует её в маршрутах раздела."""

    value: str  # noqa: WPS110

    @classmethod
    def try_parse(cls, raw_id: str) -> Optional['NetworkId']:
        if _ID_PATTERN.match(raw_id):
            return cls(raw_id)
        return None
