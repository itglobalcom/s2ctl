import asyncio
import datetime
from typing import Optional, Sequence

import click
from click.core import Context

from s2ctl.click import S2CTLCommand, echo, output_option, wait_option
from s2ctl.client import client_factory
from s2ctl.entrypoint import entry_point
from s2ctl.params import parse_date
from ssclient.llm import access_key, entities, ids, usage
from ssclient.llm.group import LlmGroupService
from ssclient.llm.llm import LlmService

GROUP_ID_ARG = 'group-id'
ACCESS_KEY_ID_ARG = 'access-key-id'

_PERIOD_DATE = click.DateTime(formats=('%Y-%m-%d',))
_GROUP_BY_VALUES = tuple(group_by.value for group_by in entities.LlmUsageGroupBy)
_SECRET_HELP = (
    'Reveal the secret of an access key.'
    + '\n\n'
    + 'The secret is given out once: a repeated call is refused, so save it right away. '
    + 'A key moved from the previous version of the service has no secret stored.'
)


def _parse_group_by(_ctx, _click_param, raw_group_by: Optional[str]) -> Optional[entities.LlmUsageGroupBy]:
    if raw_group_by is None:
        return None
    return entities.LlmUsageGroupBy(raw_group_by)


def _llm_service(ctx: Context) -> LlmService:
    return client_factory(ctx).llm()


def _group_service(ctx: Context) -> LlmGroupService:
    return _llm_service(ctx).groups()


def _access_key_service(ctx: Context) -> access_key.LlmAccessKeyService:
    return _llm_service(ctx).access_keys()


def _group_id_argument(func):
    return click.argument(GROUP_ID_ARG, required=True, type=int)(func)


def _access_key_id_argument(func):
    return click.argument(ACCESS_KEY_ID_ARG, required=True, type=int)(func)


def _tags_option(func):
    return click.option(
        '--tag',
        'tags',
        multiple=True,
        help='Tag of the whole new set of tags. May be multiple; left out, the set is cleared.',
    )(func)


@entry_point.group()
def llm():
    """Manage the LLM service of the project: connection, groups, access keys and models.

    Ids of LLM groups, access keys and models are plain integers. An access key is addressed
    by the id of its group and its own id, as printed by "key list".
    """


@llm.command(cls=S2CTLCommand)
@output_option
@click.pass_context
def connection(ctx):
    """State of the connection of the LLM service to the project."""
    echo(asyncio.run(_llm_service(ctx).connection().get()))


@llm.command(cls=S2CTLCommand)
@output_option
@wait_option
@click.option('--group-name', required=True, help='Name of the first group, up to 128 characters.')
@click.option(
    '--first-key-name',
    required=True,
    help='Name of the first access key of the group, up to 128 characters.',
)
@click.pass_context
def connect(ctx, group_name: str, first_key_name: str, wait: bool):
    """Connect the LLM service to the project with its first group and access key."""
    service_resp = asyncio.run(_llm_service(ctx).connection().connect(
        group_name=group_name, first_key_name=first_key_name, wait=wait,
    ))
    echo(service_resp)


@llm.group()
def group():
    """Manage groups of access keys and the models available to them.

    Commands take the group id, as printed by "list".
    """


@group.command('list', cls=S2CTLCommand)
@output_option
@click.pass_context
def group_list(ctx):
    """Display all LLM groups of the project; a group being created has no id yet."""
    echo(asyncio.run(_group_service(ctx).list()))


@group.command('get', cls=S2CTLCommand)
@output_option
@_group_id_argument
@click.pass_context
def group_get(ctx, group_id: ids.LlmGroupId):
    """Get information about an LLM group, its deployment and spending."""
    echo(asyncio.run(_group_service(ctx).get(group_id)))


@group.command('create', cls=S2CTLCommand)
@output_option
@wait_option
@click.option(
    '--name',
    required=True,
    help='Name of the group, up to 128 characters, unique in the project, disabled groups included.',
)
@click.pass_context
def group_create(ctx, name: str, wait: bool):
    """Create new LLM group."""
    operation = _group_service(ctx).create(name=name, wait=wait)
    echo(asyncio.run(operation))


@group.command('set-models', cls=S2CTLCommand)
@output_option
@wait_option
@_group_id_argument
@click.option(
    '--model',
    'model_ids',
    type=int,
    multiple=True,
    help='Model of the whole new set of models of the group (see "model list"). '
    + 'May be multiple; left out, every model is revoked from the group.',
)
@click.pass_context
def group_set_models(ctx, group_id: ids.LlmGroupId, model_ids: Sequence[ids.LlmModelId], wait: bool):
    """Replace the whole set of models available to an LLM group."""
    operation = _group_service(ctx).set_models(group_id, model_ids=model_ids, wait=wait)
    echo(asyncio.run(operation))


@group.command('set-tags', cls=S2CTLCommand)
@output_option
@_group_id_argument
@_tags_option
@click.pass_context
def group_set_tags(ctx, group_id: ids.LlmGroupId, tags: Sequence[str]):
    """Replace the whole set of tags of an LLM group; applied at once, without a task."""
    echo(asyncio.run(_group_service(ctx).set_tags(group_id, tags=tags)))


@group.command('disable', cls=S2CTLCommand)
@output_option
@wait_option
@_group_id_argument
@click.pass_context
def group_disable(ctx, group_id: ids.LlmGroupId, wait: bool):
    """Disable an LLM group and its access keys.

    There is no way back: a disabled group stays in the lists in state "disabled".
    """
    echo(asyncio.run(_group_service(ctx).disable(group_id, wait=wait)))


@llm.group()
def key():
    """Manage access keys to the models of the LLM service.

    Commands take the id of the group of the key and the id of the key, as printed by "list".
    """


@key.command('list', cls=S2CTLCommand)
@output_option
@click.option('--group', 'group_id', type=int, help='Show only access keys of the group.')
@click.pass_context
def key_list(ctx, group_id: Optional[ids.LlmGroupId]):
    """Display all access keys of the project; a key being issued has no id yet."""
    echo(asyncio.run(_access_key_service(ctx).list(group_id)))


@key.command('get', cls=S2CTLCommand)
@output_option
@_group_id_argument
@_access_key_id_argument
@click.pass_context
def key_get(ctx, group_id: ids.LlmGroupId, access_key_id: ids.LlmAccessKeyId):
    """Get information about an access key: its locks, tags, spending and expiry."""
    echo(asyncio.run(_access_key_service(ctx).get(group_id, access_key_id)))


@key.command('issue', cls=S2CTLCommand)
@output_option
@wait_option
@_group_id_argument
@click.option('--name', required=True, help='Name of the access key, up to 128 characters.')
@click.pass_context
def key_issue(ctx, group_id: ids.LlmGroupId, name: str, wait: bool):
    """Issue new access key in an LLM group; its secret is revealed by "secret"."""
    operation = _access_key_service(ctx).issue(group_id, name=name, wait=wait)
    echo(asyncio.run(operation))


@key.command('secret', cls=S2CTLCommand, help=_SECRET_HELP)
@output_option
@_group_id_argument
@_access_key_id_argument
@click.pass_context
def key_secret(ctx, group_id: ids.LlmGroupId, access_key_id: ids.LlmAccessKeyId):
    echo(asyncio.run(_access_key_service(ctx).reveal_secret(group_id, access_key_id)))


@key.command('lock', cls=S2CTLCommand)
@output_option
@wait_option
@_group_id_argument
@_access_key_id_argument
@click.option('--reason', help='Why the key is locked.')
@click.pass_context
def key_lock(
    ctx, group_id: ids.LlmGroupId, access_key_id: ids.LlmAccessKeyId, reason: Optional[str], wait: bool,
):
    """Lock an access key."""
    service_resp = asyncio.run(_access_key_service(ctx).lock(
        group_id, access_key_id, reason=reason, wait=wait,
    ))
    echo(service_resp)


@key.command('unlock', cls=S2CTLCommand)
@output_option
@wait_option
@_group_id_argument
@_access_key_id_argument
@click.pass_context
def key_unlock(ctx, group_id: ids.LlmGroupId, access_key_id: ids.LlmAccessKeyId, wait: bool):
    """Remove the lock of an access key set by "lock"."""
    operation = _access_key_service(ctx).unlock(group_id, access_key_id, wait=wait)
    echo(asyncio.run(operation))


@key.command('delete', cls=S2CTLCommand)
@output_option
@wait_option
@_group_id_argument
@_access_key_id_argument
@click.pass_context
def key_delete(ctx, group_id: ids.LlmGroupId, access_key_id: ids.LlmAccessKeyId, wait: bool):
    """Delete an access key."""
    operation = _access_key_service(ctx).delete(group_id, access_key_id, wait=wait)
    echo(asyncio.run(operation))


@key.command('set-tags', cls=S2CTLCommand)
@output_option
@_group_id_argument
@_access_key_id_argument
@_tags_option
@click.pass_context
def key_set_tags(ctx, group_id: ids.LlmGroupId, access_key_id: ids.LlmAccessKeyId, tags: Sequence[str]):
    """Replace the whole set of tags of an access key; applied at once, without a task."""
    operation = _access_key_service(ctx).set_tags(group_id, access_key_id, tags=tags)
    echo(asyncio.run(operation))


@llm.group()
def model():
    """Catalogue of the models of the LLM service available to the project."""


@model.command('list', cls=S2CTLCommand)
@output_option
@click.pass_context
def model_list(ctx):
    """Display the catalogue of models with their starting prices and the price of a credit."""
    echo(asyncio.run(_llm_service(ctx).models().list()))


@model.command('get', cls=S2CTLCommand)
@output_option
@click.argument('model-id', required=True, type=int)
@click.pass_context
def model_get(ctx, model_id: ids.LlmModelId):
    """Get information about a model: its prices, providers and capabilities."""
    echo(asyncio.run(_llm_service(ctx).models().get(model_id)))


@llm.group()
def package():
    """Packages of credits of the LLM service."""


@package.command('get', cls=S2CTLCommand)
@output_option
@click.pass_context
def package_get(ctx):
    """Current package of the project and the spending of its open period."""
    echo(asyncio.run(_llm_service(ctx).package().get()))


@package.command('plans', cls=S2CTLCommand)
@output_option
@click.pass_context
def package_plans(ctx):
    """Plans of packages available to the project."""
    echo(asyncio.run(_llm_service(ctx).package().plans()))


@llm.command('usage', cls=S2CTLCommand)
@output_option
@click.option(
    '--from',
    'period_from',
    type=_PERIOD_DATE,
    required=True,
    callback=parse_date,
    help='First day of the period, YYYY-MM-DD, inclusive.',
)
@click.option(
    '--to',
    'period_to',
    type=_PERIOD_DATE,
    required=True,
    callback=parse_date,
    help='Last day of the period, YYYY-MM-DD, inclusive; the period is at most 366 days.',
)
@click.option(
    '--group-by',
    type=click.Choice(_GROUP_BY_VALUES),
    callback=_parse_group_by,
    help='Split the spending into rows by day, model, group or access key; "none" prints the totals only.',
)
@click.option('--group', 'group_id', type=int, help='Count only the spending of the group.')
@click.option('--key', 'access_key_id', type=int, help='Count only the spending of the access key.')
@click.option('--model', 'model_id', type=int, help='Count only the spending on the model.')
@click.pass_context
def llm_usage(
    ctx,
    period_from: datetime.date,
    period_to: datetime.date,
    group_by: Optional[entities.LlmUsageGroupBy],
    group_id: Optional[ids.LlmGroupId],
    access_key_id: Optional[ids.LlmAccessKeyId],
    model_id: Optional[ids.LlmModelId],
):
    """Spending of the LLM service over a period: credits, money and tokens."""
    query = usage.LlmUsageQuery(
        period_from=period_from,
        period_to=period_to,
        group_by=group_by,
        group_id=group_id,
        access_key_id=access_key_id,
        model_id=model_id,
    )
    echo(asyncio.run(_llm_service(ctx).usage().usage(query)))


@llm.command(cls=S2CTLCommand)
@output_option
@click.pass_context
def requests(ctx):
    """Requests made with the access keys of the project over the last 7 days, up to 200."""
    echo(asyncio.run(_llm_service(ctx).usage().requests()))
