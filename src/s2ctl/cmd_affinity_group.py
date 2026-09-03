import asyncio

import click
from click.core import Context

from s2ctl.click import S2CTLCommand, echo, output_option, wait_option
from s2ctl.client import client_factory
from s2ctl.entrypoint import entry_point
from s2ctl.params import parse_affinity_group_id
from ssclient.affinity_group import AffinityGroupService
from ssclient.affinity_group_id import AffinityGroupId

AFFINITY_GROUP_ID_ARG = 'affinity-group-id'


def _get_affinity_group_service(ctx: Context) -> AffinityGroupService:
    return ctx.obj['affinity_group_service']


@entry_point.group('affinity-group')
@click.pass_context
def affinity_group(ctx):
    """Manage affinity and anti-affinity groups of servers."""
    client = client_factory(ctx)
    ctx.obj['affinity_group_service'] = client.affinity_groups()


@affinity_group.command(cls=S2CTLCommand)
@output_option
@click.option('--location', required=True, help='Where to create a group (see "locations" command).')
@click.option('--name', required=True, help='Name of new group.')
@click.option(
    '--affinity/--anti-affinity',
    'affinity',
    required=True,
    help='Affinity keeps servers of the group on one host, anti-affinity spreads them over hosts.',
)
@click.pass_context
def create(ctx, location: str, name: str, affinity: bool):
    """Create new affinity or anti-affinity group."""
    group_service = _get_affinity_group_service(ctx)
    service_resp = asyncio.run(
        group_service.create(location_id=location, name=name, affinity=affinity),
    )
    echo(service_resp)


@affinity_group.command('list', cls=S2CTLCommand)
@output_option
@click.pass_context
def groups_list(ctx):
    """Display all affinity and anti-affinity groups in the project."""
    group_service = _get_affinity_group_service(ctx)
    service_resp = asyncio.run(group_service.list())
    echo(service_resp)


@affinity_group.command(cls=S2CTLCommand)
@output_option
@click.argument(AFFINITY_GROUP_ID_ARG, required=True, callback=parse_affinity_group_id)
@click.pass_context
def get(ctx, affinity_group_id: AffinityGroupId):
    """Get information about a group."""
    group_service = _get_affinity_group_service(ctx)
    service_resp = asyncio.run(group_service.get(group_id=affinity_group_id))
    echo(service_resp)


@affinity_group.command(cls=S2CTLCommand)
@output_option
@wait_option
@click.argument(AFFINITY_GROUP_ID_ARG, required=True, callback=parse_affinity_group_id)
@click.pass_context
def delete(ctx, affinity_group_id: AffinityGroupId, wait: bool):
    """Delete a group. Servers of the group are kept."""
    group_service = _get_affinity_group_service(ctx)
    service_resp = asyncio.run(group_service.delete(group_id=affinity_group_id, wait=wait))
    echo(service_resp)
