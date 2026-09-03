import re
from typing import NamedTuple, Optional

AFFINITY_GROUP_ID_TEMPLATE = 'l<location>g<group>'

_ID_PATTERN = re.compile(r'^l\d+g\d+$')


class AffinityGroupId(NamedTuple):
    """Составной id группы: так publisher адресует её в маршрутах чтения и удаления."""

    value: str  # noqa: WPS110

    @classmethod
    def try_parse(cls, raw_id: str) -> Optional['AffinityGroupId']:
        if _ID_PATTERN.match(raw_id):
            return cls(raw_id)
        return None
