import re
from typing import NamedTuple, Optional

SERVER_ID_TEMPLATE = 'l<location>s<server>'

_ID_PATTERN = re.compile(r'^l\d+s\d+$')


class ServerId(NamedTuple):
    """Составной id vStack-сервера: так publisher адресует его в маршрутах раздела."""

    value: str  # noqa: WPS110

    @classmethod
    def try_parse(cls, raw_id: str) -> Optional['ServerId']:
        if _ID_PATTERN.match(raw_id):
            return cls(raw_id)
        return None
