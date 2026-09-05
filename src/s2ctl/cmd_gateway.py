import asyncio
from typing import Any, Optional, Sequence

import click
from click.core import Context

from s2ctl.click import S2CTLCommand, echo, output_option, wait_option
from s2ctl.client import client_factory
from s2ctl.entrypoint import entry_point
from s2ctl.params import parse_gateway_id, parse_network_id, parse_network_ids, rules_file_option
from ssclient.gateway.gateway import GatewayService
from ssclient.gateway.gateway_id import GATEWAY_ID_TEMPLATE, GatewayId
from ssclient.network.network_id import NetworkId

GATEWAY_ID_ARG = 'gateway-id'

_GROUP_HELP = (
    'Manage edge gateways connecting isolated networks to the Internet.'
    + '\n\n'
    + 'Commands take the gateway id in the {template} format, as printed by "list".'
).format(template=GATEWAY_ID_TEMPLATE)


def _get_gateway_service(ctx: Context) -> GatewayService:
    return client_factory(ctx).gateways()


@entry_point.group(help=_GROUP_HELP)
def gateway():
    """Manage edge gateways connecting isolated networks to the Internet."""


@gateway.command(cls=S2CTLCommand)
@output_option
@wait_option
@click.option('--location', required=True, help='Where to create a gateway (see "locations" command).')
@click.option('--name', required=True, help='Name of new gateway.')
@click.option(
    '--bandwidth',
    type=int,
    help='Public network interface bandwidth in Mbps, the value must be a multiple of 10 Mbps.',
)
@click.option(
    '--network-id',
    'network_ids',
    multiple=True,
    required=True,
    callback=parse_network_ids,
    help='Isolated network to connect to the gateway (see "network" command). '
    + 'May be multiple, up to 3 networks.',
)
@click.pass_context
def create(
    ctx,
    location: str,
    name: str,
    bandwidth: Optional[int],
    network_ids: Sequence[NetworkId],
    wait: bool,
):
    """Create new edge gateway."""
    gateway_service = _get_gateway_service(ctx)
    service_resp = asyncio.run(gateway_service.create(
        location_id=location,
        name=name,
        bandwidth_mbps=bandwidth,
        network_ids=network_ids,
        wait=wait,
    ))
    echo(service_resp)


@gateway.command('list', cls=S2CTLCommand)
@output_option
@click.option('--location', help='Show only gateways of the location (see "locations" command).')
@click.pass_context
def gateways_list(ctx, location: Optional[str]):
    """Display all edge gateways in the project."""
    gateway_service = _get_gateway_service(ctx)
    service_resp = asyncio.run(gateway_service.list(location_id=location))
    echo(service_resp)


@gateway.command(cls=S2CTLCommand)
@output_option
@click.argument(GATEWAY_ID_ARG, required=True, callback=parse_gateway_id)
@click.pass_context
def get(ctx, gateway_id: GatewayId):
    """Get information about a gateway."""
    gateway_service = _get_gateway_service(ctx)
    service_resp = asyncio.run(gateway_service.get(gateway_id=gateway_id))
    echo(service_resp)


@gateway.command(cls=S2CTLCommand)
@output_option
@click.argument(GATEWAY_ID_ARG, required=True, callback=parse_gateway_id)
@click.option('--name', required=True, help='New name of the gateway.')
@click.pass_context
def rename(ctx, gateway_id: GatewayId, name: str):
    """Change the name of a gateway."""
    gateway_service = _get_gateway_service(ctx)
    service_resp = asyncio.run(gateway_service.rename(gateway_id=gateway_id, name=name))
    echo(service_resp)


@gateway.command('set-bandwidth', cls=S2CTLCommand)
@output_option
@wait_option
@click.argument(GATEWAY_ID_ARG, required=True, callback=parse_gateway_id)
@click.option(
    '--bandwidth',
    type=int,
    required=True,
    help='Public network interface bandwidth in Mbps, the value must be a multiple of 10 Mbps.',
)
@click.pass_context
def set_bandwidth(ctx, gateway_id: GatewayId, bandwidth: int, wait: bool):
    """Set the bandwidth of the public network interface of a gateway."""
    gateway_service = _get_gateway_service(ctx)
    service_resp = asyncio.run(gateway_service.set_bandwidth(
        gateway_id=gateway_id, bandwidth_mbps=bandwidth, wait=wait,
    ))
    echo(service_resp)


@gateway.command(cls=S2CTLCommand)
@output_option
@wait_option
@click.argument(GATEWAY_ID_ARG, required=True, callback=parse_gateway_id)
@click.pass_context
def delete(ctx, gateway_id: GatewayId, wait: bool):
    """Delete a gateway."""
    gateway_service = _get_gateway_service(ctx)
    service_resp = asyncio.run(gateway_service.delete(gateway_id=gateway_id, wait=wait))
    echo(service_resp)


@gateway.command('get-firewall', cls=S2CTLCommand)
@output_option
@click.argument(GATEWAY_ID_ARG, required=True, callback=parse_gateway_id)
@click.pass_context
def get_firewall(ctx, gateway_id: GatewayId):
    """Display the firewall rules of a gateway."""
    firewall_service = _get_gateway_service(ctx).firewall(gateway_id=gateway_id)
    service_resp = asyncio.run(firewall_service.get())
    echo(service_resp)


@gateway.command('replace-firewall', cls=S2CTLCommand)
@output_option
@wait_option
@rules_file_option
@click.argument(GATEWAY_ID_ARG, required=True, callback=parse_gateway_id)
@click.pass_context
def replace_firewall(ctx, gateway_id: GatewayId, rules: Sequence[Any], wait: bool):
    """Replace the whole firewall rule set of a gateway with the given one."""
    firewall_service = _get_gateway_service(ctx).firewall(gateway_id=gateway_id)
    service_resp = asyncio.run(firewall_service.replace(rules, wait=wait))
    echo(service_resp)


@gateway.command('get-nat', cls=S2CTLCommand)
@output_option
@click.argument(GATEWAY_ID_ARG, required=True, callback=parse_gateway_id)
@click.pass_context
def get_nat(ctx, gateway_id: GatewayId):
    """Display the NAT rules of a gateway."""
    nat_service = _get_gateway_service(ctx).nat(gateway_id=gateway_id)
    service_resp = asyncio.run(nat_service.get())
    echo(service_resp)


@gateway.command('replace-nat', cls=S2CTLCommand)
@output_option
@wait_option
@rules_file_option
@click.argument(GATEWAY_ID_ARG, required=True, callback=parse_gateway_id)
@click.pass_context
def replace_nat(ctx, gateway_id: GatewayId, rules: Sequence[Any], wait: bool):
    """Replace the whole NAT rule set of a gateway with the given one."""
    nat_service = _get_gateway_service(ctx).nat(gateway_id=gateway_id)
    service_resp = asyncio.run(nat_service.replace(rules, wait=wait))
    echo(service_resp)


@gateway.command('add-nic', cls=S2CTLCommand)
@output_option
@wait_option
@click.argument(GATEWAY_ID_ARG, required=True, callback=parse_gateway_id)
@click.option(
    '--network-id',
    required=True,
    callback=parse_network_id,
    help='Isolated network to connect to the gateway (see "network" command).',
)
@click.pass_context
def add_nic(ctx, gateway_id: GatewayId, network_id: NetworkId, wait: bool):
    """Connect an isolated network to a gateway."""
    nic_service = _get_gateway_service(ctx).nics(gateway_id=gateway_id)
    service_resp = asyncio.run(nic_service.create(network_id=network_id, wait=wait))
    echo(service_resp)


@gateway.command('delete-nic', cls=S2CTLCommand)
@output_option
@wait_option
@click.argument(GATEWAY_ID_ARG, required=True, callback=parse_gateway_id)
@click.option('--nic-id', type=int, required=True, help='Network interface identifier.')
@click.pass_context
def delete_nic(ctx, gateway_id: GatewayId, nic_id: int, wait: bool):
    """Disconnect an isolated network from a gateway."""
    nic_service = _get_gateway_service(ctx).nics(gateway_id=gateway_id)
    service_resp = asyncio.run(nic_service.delete(nic_id=nic_id, wait=wait))
    echo(service_resp)


@gateway.command(cls=S2CTLCommand)
@output_option
@wait_option
@click.argument(GATEWAY_ID_ARG, required=True, callback=parse_gateway_id)
@click.pass_context
def start(ctx, gateway_id: GatewayId, wait: bool):
    """Power on a gateway."""
    power_service = _get_gateway_service(ctx).power(gateway_id=gateway_id)
    service_resp = asyncio.run(power_service.start(wait=wait))
    echo(service_resp)


@gateway.command(cls=S2CTLCommand)
@output_option
@wait_option
@click.argument(GATEWAY_ID_ARG, required=True, callback=parse_gateway_id)
@click.pass_context
def stop(ctx, gateway_id: GatewayId, wait: bool):
    """Power off a gateway."""
    power_service = _get_gateway_service(ctx).power(gateway_id=gateway_id)
    service_resp = asyncio.run(power_service.stop(wait=wait))
    echo(service_resp)


@gateway.command(cls=S2CTLCommand)
@output_option
@wait_option
@click.argument(GATEWAY_ID_ARG, required=True, callback=parse_gateway_id)
@click.pass_context
def restart(ctx, gateway_id: GatewayId, wait: bool):
    """Restart a gateway."""
    power_service = _get_gateway_service(ctx).power(gateway_id=gateway_id)
    service_resp = asyncio.run(power_service.restart(wait=wait))
    echo(service_resp)


@gateway.command('add-tag', cls=S2CTLCommand)
@output_option
@click.argument(GATEWAY_ID_ARG, required=True, callback=parse_gateway_id)
@click.option('--name', required=True, help='Name of tag.')
@click.pass_context
def add_tag(ctx, gateway_id: GatewayId, name: str):
    """Add tag to a gateway."""
    tag_service = _get_gateway_service(ctx).tags(gateway_id=gateway_id)
    service_resp = asyncio.run(tag_service.create(name=name))
    echo(service_resp)


@gateway.command('delete-tag', cls=S2CTLCommand)
@output_option
@click.argument(GATEWAY_ID_ARG, required=True, callback=parse_gateway_id)
@click.option('--name', required=True, help='Name of tag.')
@click.pass_context
def delete_tag(ctx, gateway_id: GatewayId, name: str):
    """Remove tag from a gateway."""
    tag_service = _get_gateway_service(ctx).tags(gateway_id=gateway_id)
    service_resp = asyncio.run(tag_service.delete(name=name))
    echo(service_resp)
