import json
from typing import IO, Any, List, Optional, Sequence, Tuple

import click

from ssclient.network.network_id import NETWORK_ID_TEMPLATE, NetworkId

RULES_FILE_HELP = (
    'Path to the file with the whole rule set in JSON, as printed by the matching '
    + '"get-*" command with "--output json" — either the array of rules itself or the '
    + 'object carrying it in "rules". Pass "-" to read the set from stdin.'
)

_NETWORK_ID_HINT = 'network id format: {template}'.format(template=NETWORK_ID_TEMPLATE)
_RULES_FIELD = 'rules'


def parse_network_id(_ctx, _click_param, raw_id: Optional[str]) -> Optional[NetworkId]:
    if raw_id is None:
        return None
    return _require_network_id(raw_id)


def parse_network_ids(_ctx, _click_param, raw_ids: Sequence[str]) -> Tuple[NetworkId, ...]:
    return tuple(_require_network_id(raw_id) for raw_id in raw_ids)


def parse_rules(_ctx, _click_param, rules_file: IO) -> List[Any]:
    try:
        rules = json.load(rules_file)
    except ValueError as exc:
        raise click.BadParameter('file content is not valid JSON') from exc

    if isinstance(rules, dict):
        # `vmware edge get-firewall` печатает набор правил внутри объекта, вместе
        # с состоянием самого экрана: round-trip принимает и такой файл.
        rules = rules.get(_RULES_FIELD)
    if not isinstance(rules, list):
        raise click.BadParameter('file must contain a JSON array of rules')
    return rules


def rules_file_option(func):
    return click.option(
        '--rules-file',
        'rules',
        type=click.File('r'),
        required=True,
        callback=parse_rules,
        help=RULES_FILE_HELP,
    )(func)


def _require_network_id(raw_id: str) -> NetworkId:
    network_id = NetworkId.try_parse(raw_id)
    if network_id is None:
        raise click.BadParameter(_NETWORK_ID_HINT)
    return network_id
