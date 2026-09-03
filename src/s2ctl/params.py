import json
from typing import IO, Any, List, Optional, Sequence, Tuple, TypeVar

import click

from ssclient.affinity_group_id import AFFINITY_GROUP_ID_TEMPLATE, AffinityGroupId
from ssclient.gateway.gateway_id import GATEWAY_ID_TEMPLATE, GatewayId
from ssclient.network.network_id import NETWORK_ID_TEMPLATE, NetworkId
from ssclient.task_id import TaskId, supported_formats_hint

RULES_FILE_HELP = (
    'Path to the file with the whole rule set in JSON, as printed by the matching '
    + '"get-*" command with "--output json" — either the array of rules itself or the '
    + 'object carrying it in "rules". Pass "-" to read the set from stdin. '
    + 'For "vmware edge update-firewall" the round trip is lossy: the request of the API '
    + 'has no per-rule "enabled" and "description", so these two fields of a rule printed '
    + 'by "get-firewall" are dropped.'
)

_NETWORK_ID_HINT = 'network id format: {template}'.format(template=NETWORK_ID_TEMPLATE)
_GATEWAY_ID_HINT = 'gateway id format: {template}'.format(template=GATEWAY_ID_TEMPLATE)
_GROUP_ID_HINT = 'affinity group id format: {template}'.format(
    template=AFFINITY_GROUP_ID_TEMPLATE,
)
_TASK_ID_HINT = 'supported task id formats: {hint}'.format(hint=supported_formats_hint())
_RULES_FIELD = 'rules'

_ParsedId = TypeVar('_ParsedId')


def parse_network_id(_ctx, _click_param, raw_id: Optional[str]) -> Optional[NetworkId]:
    if raw_id is None:
        return None
    return _parsed(NetworkId.try_parse(raw_id), _NETWORK_ID_HINT)


def parse_network_ids(_ctx, _click_param, raw_ids: Sequence[str]) -> Tuple[NetworkId, ...]:
    return tuple(
        _parsed(NetworkId.try_parse(raw_id), _NETWORK_ID_HINT) for raw_id in raw_ids
    )


def parse_gateway_id(_ctx, _click_param, raw_id: str) -> GatewayId:
    return _parsed(GatewayId.try_parse(raw_id), _GATEWAY_ID_HINT)


def parse_affinity_group_id(_ctx, _click_param, raw_id: str) -> AffinityGroupId:
    return _parsed(AffinityGroupId.try_parse(raw_id), _GROUP_ID_HINT)


def parse_task_id(_ctx, _click_param, raw_id: str) -> TaskId:
    return _parsed(TaskId.try_parse(raw_id), _TASK_ID_HINT)


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


def _parsed(parsed_id: Optional[_ParsedId], hint: str) -> _ParsedId:
    """Разбор составного id падает до запроса: пользователь видит формат, а не отказ API."""
    if parsed_id is None:
        raise click.BadParameter(hint)
    return parsed_id
