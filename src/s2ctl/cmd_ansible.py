import asyncio
from collections import defaultdict
from typing import Any, DefaultDict, Dict, List, Optional

import click
from click import Context

from s2ctl.click import S2CTLCommand, echo, output_option
from s2ctl.client import client_factory
from s2ctl.entrypoint import entry_point
from s2ctl.formatters import YAMLFormatter
from ssclient.network.network import NetworkService
from ssclient.server.server import ServerEntity, ServerNicEntity, ServerService


def _get_server_serivce(ctx: Context) -> ServerService:
    return ctx.obj['server_service']


def _get_net_serivce(ctx) -> NetworkService:
    return ctx.obj['network_service']


@entry_point.group()
@click.pass_context
def ansible(ctx):
    """Set of ansible management commands."""
    client = client_factory(ctx)
    ctx.obj['server_service'] = client.servers()
    ctx.obj['network_service'] = client.networks()


@ansible.command(cls=S2CTLCommand)
@output_option
@click.pass_context
def get_inventory(ctx):
    """Get ansible inventory."""
    networks = asyncio.run(_get_net_serivce(ctx).list())
    servers = asyncio.run(_get_server_serivce(ctx).list())

    isolated_network_ids = [network['id'] for network in networks]
    inventory_resp = _generate_inventory(servers, isolated_network_ids)
    echo(inventory_resp, formatter=YAMLFormatter())


def _generate_inventory(
    servers: List[ServerEntity], isolated_network_ids: List[str],
) -> Dict[str, Any]:
    without_tags: List[str] = []
    tagged_ips: DefaultDict[str, List[str]] = defaultdict(list)

    for server in servers:
        nic = _get_server_public_connection(server, isolated_network_ids)
        if nic:
            if server['tags']:
                for tag in server['tags']:
                    tagged_ips[tag].append(nic['ip_address'])
            else:
                without_tags.append(nic['ip_address'])

    return _format_inventory_groups(without_tags, tagged_ips)


def _get_server_public_connection(
    server: ServerEntity, isolated_network_ids: List[str],
) -> Optional[ServerNicEntity]:
    nics = sorted(server['nics'], key=lambda _nic: _nic['id'])

    for nic in nics:
        # looking for any public network connection
        if nic['network_id'] not in isolated_network_ids:
            return nic
    return None


def _format_inventory_groups(
    without_tags: List[str], tagged_ips: Dict[str, List[str]],
) -> Dict[str, Any]:
    inventory = {'all': {}}

    if without_tags:
        inventory['all']['hosts'] = {ip: {} for ip in without_tags}

    children = {}
    for group, ip_list in tagged_ips.items():
        hosts = {ip: {} for ip in ip_list}
        children[group] = {'hosts': hosts}

    inventory['all']['children'] = children

    return inventory
