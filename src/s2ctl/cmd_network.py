import asyncio

import click

from s2ctl.click import S2CTLCommand, echo, output_option, wait_option
from s2ctl.client import client_factory
from s2ctl.entrypoint import entry_point
from s2ctl.params import parse_network_id
from ssclient.network.network import NetworkService
from ssclient.network.network_id import NETWORK_ID_TEMPLATE, NetworkId

_GROUP_HELP = (
    'Manage isolated networks without Internet access.'
    + '\n\n'
    + 'Commands take the network id in the {template} format, as printed by "list".'
).format(template=NETWORK_ID_TEMPLATE)


def _get_net_serivce(ctx) -> NetworkService:
    return client_factory(ctx).networks()


@entry_point.group(help=_GROUP_HELP)
def network():
    """Manage isolated networks without Internet access."""


@network.command(cls=S2CTLCommand)
@output_option
@wait_option
@click.option('--location', required=True, help='Where to create a network (see "locations" command).')
@click.option('--name', required=True, help='Name of creating network.')
@click.option('--description', required=True, help='Long description of creating network.')
@click.option('--network-prefix', required=True, help='Network address.')
@click.option(
    '--mask',
    type=int,
    required=True,
    help='The count of leading 1 bits in the routing mask '
    + '(e.g. 24 is equivalent to the 255.255.255.0).',
)
@click.pass_context
def create(
    ctx,
    location: str,
    name: str,
    description: str,
    network_prefix: str,
    mask: int,
    wait: bool,
):
    """Create new isolated network."""
    net_service = _get_net_serivce(ctx)
    service_resp = asyncio.run(net_service.create(
        location_id=location,
        name=name,
        description=description,
        network_prefix=network_prefix,
        mask=mask,
        wait=wait,
    ))
    echo(service_resp)


@network.command('list', cls=S2CTLCommand)
@output_option
@click.pass_context
def list_network(ctx):
    """Display all isolated networks in the project."""
    net_service = _get_net_serivce(ctx)
    service_resp = asyncio.run(net_service.list())
    echo(service_resp)


@network.command(cls=S2CTLCommand)
@output_option
@click.argument('network-id', required=True, callback=parse_network_id)
@click.pass_context
def get(ctx, network_id: NetworkId):
    """Get information about a network."""
    net_service = _get_net_serivce(ctx)
    service_resp = asyncio.run(net_service.get(network_id=network_id))
    echo(service_resp)


@network.command(cls=S2CTLCommand)
@output_option
@click.argument('network-id', required=True, callback=parse_network_id)
@click.option('--name', required=True, help='New name of the network.')
@click.option('--description', required=True, help='New long description of the network.')
@click.pass_context
def edit(ctx, network_id: NetworkId, name: str, description: str):
    """Update network information."""
    net_service = _get_net_serivce(ctx)
    service_resp = asyncio.run(net_service.update(
        network_id=network_id,
        name=name,
        description=description,
    ))
    echo(service_resp)


@network.command(cls=S2CTLCommand)
@output_option
@click.argument('network-id', required=True, callback=parse_network_id)
@click.pass_context
def delete(ctx, network_id: NetworkId):
    """Delete a network."""
    net_service = _get_net_serivce(ctx)
    service_resp = asyncio.run(net_service.delete(network_id=network_id))
    echo(service_resp)


@network.command(cls=S2CTLCommand)
@output_option
@click.argument('network-id', required=True, callback=parse_network_id)
@click.option('--name', required=True, help='Name of tag.')
@click.pass_context
def add_tag(ctx, network_id: NetworkId, name: str):
    """Add tag to network."""
    net_service = _get_net_serivce(ctx)
    tag_service = net_service.tags(network_id=network_id)
    service_resp = asyncio.run(tag_service.create(name=name))
    echo(service_resp)


@network.command(cls=S2CTLCommand)
@output_option
@click.argument('network-id', required=True, callback=parse_network_id)
@click.option('--name', type=str, required=True, help='Name of tag.')
@click.pass_context
def delete_tag(ctx, network_id: NetworkId, name: str):
    """Remove tag from network."""
    net_service = _get_net_serivce(ctx)
    tag_service = net_service.tags(network_id=network_id)
    service_resp = asyncio.run(
        tag_service.delete(name=name),
    )
    echo(service_resp)
