from typing import Optional, Sequence, Tuple

import click

from ssclient.network.network_id import NETWORK_ID_TEMPLATE, NetworkId

_NETWORK_ID_HINT = 'network id format: {template}'.format(template=NETWORK_ID_TEMPLATE)


def parse_network_id(_ctx, _click_param, raw_id: Optional[str]) -> Optional[NetworkId]:
    if raw_id is None:
        return None
    return _require_network_id(raw_id)


def parse_network_ids(_ctx, _click_param, raw_ids: Sequence[str]) -> Tuple[NetworkId, ...]:
    return tuple(_require_network_id(raw_id) for raw_id in raw_ids)


def _require_network_id(raw_id: str) -> NetworkId:
    network_id = NetworkId.try_parse(raw_id)
    if network_id is None:
        raise click.BadParameter(_NETWORK_ID_HINT)
    return network_id
