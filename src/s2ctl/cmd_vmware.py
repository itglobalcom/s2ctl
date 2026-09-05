import asyncio
from typing import Any, Optional, Sequence, Tuple

import click
from click.core import Context

from s2ctl.click import S2CTLCommand, echo, output_option, wait_option
from s2ctl.client import client_factory
from s2ctl.entrypoint import entry_point
from s2ctl.params import rules_file_option
from ssclient.vmware.edge import VmwareEdgeService
from ssclient.vmware.ids import VmwareLocationId, VmwareNatRuleId, VmwareNetworkId, VmwareServerId, VmwareVpnTunnelId
from ssclient.vmware.network import VmwareNetworkService, VmwareServerNic
from ssclient.vmware.vmware import VmwareService

NETWORK_ID_ARG = 'network-id'

_LOCATION_HELP = 'Location identifier (see "vmware locations" command).'
_SERVER_NIC_HINT = 'server format: SERVER_ID[:IP], e.g. "42" or "42:10.0.0.5"'

# Закрытые множества значений контракта: publisher принимает имена членов enum
# без учёта регистра и в таком же виде публикует их в справочнике API.
_NETWORK_TYPES = ('private_client', 'routed_client', 'public_client', 'public_shared', 'public_shared_ipv6')
_NETWORK_CAPACITIES = ('Network24', 'Network25', 'Network26', 'Network27', 'Network28', 'Network29')
_IMAGE_GPU_FILTERS = ('required', 'unsupported')
_FIREWALL_ACTIONS = ('Allow', 'Deny')
_PROTOCOLS = ('Any', 'Tcp', 'Udp', 'TcpAndUdp', 'Icmp')
_NAT_RULE_TYPES = ('SNAT', 'DNAT')
_ADDRESS_IS_REQUIRED = (
    '{option} is required for a {rule_type} rule: the platform supplies the other address '
    + 'of the rule itself, this one it takes from you.'
)
_VPN_ENCRYPTION_TYPES = ('Aes', 'Aes256', 'TripleDes', 'AesGcm')
_DIFFIE_HELLMAN_GROUPS = ('DH2', 'DH5', 'DH14', 'DH15', 'DH16')


def vmware_service(ctx: Context) -> VmwareService:
    """Сервис услуги VMware: на нём строятся команды подгрупп `network`, `edge` и `server`."""
    return client_factory(ctx).vmware()


def _network_service(ctx: Context) -> VmwareNetworkService:
    return vmware_service(ctx).networks()


def _edge_service(ctx: Context, network_id: VmwareNetworkId) -> VmwareEdgeService:
    return vmware_service(ctx).networks().edge(network_id)


def _parse_server_nics(_ctx, _click_param, raw_nics: Sequence[str]) -> Tuple[VmwareServerNic, ...]:
    return tuple(_parse_server_nic(raw_nic) for raw_nic in raw_nics)


def _parse_server_nic(raw_nic: str) -> VmwareServerNic:
    raw_server_id, _, ip_address = raw_nic.partition(':')
    if not raw_server_id.isdigit():
        raise click.BadParameter(_SERVER_NIC_HINT)
    return VmwareServerNic(server_id=VmwareServerId(int(raw_server_id)), ip=ip_address or None)


def _check_rule_addresses(
    rule_type: str, original_ip: Optional[str], translated_ip: Optional[str],
) -> None:
    """Адрес правила NAT, который платформа за пользователя не подставляет.

    В original_ip DNAT-правила платформа всегда пишет внешний адрес самого edge (NET-4),
    в translated_ip SNAT-правила — адрес трансляции; обязателен ровно второй адрес правила.
    """
    snat, dnat = _NAT_RULE_TYPES
    requested_type = rule_type.upper()
    if requested_type == snat and not original_ip:
        raise click.UsageError(_ADDRESS_IS_REQUIRED.format(option='--original-ip', rule_type=snat))
    if requested_type == dnat and not translated_ip:
        raise click.UsageError(_ADDRESS_IS_REQUIRED.format(option='--translated-ip', rule_type=dnat))


def _network_id_argument(func):
    return click.argument(NETWORK_ID_ARG, required=True, type=int)(func)


@entry_point.group()
def vmware():
    """Manage VMware Cloud resources: catalogs, networks and their edge gateways.

    Ids of VMware resources are plain integers, not the composite ids of the vStack sections.
    """


@vmware.command(cls=S2CTLCommand)
@output_option
@click.pass_context
def locations(ctx):
    """List of VMware locations available to the project."""
    service_resp = asyncio.run(vmware_service(ctx).locations().list())
    echo(service_resp)


@vmware.command(cls=S2CTLCommand)
@output_option
@click.option('--location', type=int, help='Show only images of the location.')
@click.option(
    '--gpu',
    type=click.Choice(_IMAGE_GPU_FILTERS, case_sensitive=False),
    help='Show only images that require a GPU ("required") or cannot use one ("unsupported").',
)
@click.pass_context
def images(ctx, location: Optional[VmwareLocationId], gpu: Optional[str]):
    """List of OS templates which you can use for your VMware server."""
    images_service = vmware_service(ctx).images()
    service_resp = asyncio.run(images_service.list(location_id=location, gpu=gpu))
    echo(service_resp)


@vmware.command('gpu-models', cls=S2CTLCommand)
@output_option
@click.option('--location', type=int, help='Show only GPU models offered in the location.')
@click.pass_context
def gpu_models(ctx, location: Optional[VmwareLocationId]):
    """List of GPU models which you can attach to your VMware server."""
    service_resp = asyncio.run(vmware_service(ctx).gpu_models().list(location_id=location))
    echo(service_resp)


@vmware.group()
def network():
    """Manage VMware networks.

    Commands take the network id, as printed by "list".
    """


@network.command('list', cls=S2CTLCommand)
@output_option
@click.option('--location', type=int, help='Show only networks of the location.')
@click.option(
    '--type',
    'network_type',
    type=click.Choice(_NETWORK_TYPES, case_sensitive=False),
    help='Show only networks of the type.',
)
@click.pass_context
def networks_list(ctx, location: Optional[VmwareLocationId], network_type: Optional[str]):
    """Display all VMware networks in the project."""
    service_resp = asyncio.run(_network_service(ctx).list(location_id=location, network_type=network_type))
    echo(service_resp)


@network.command(cls=S2CTLCommand)
@output_option
@_network_id_argument
@click.pass_context
def get(ctx, network_id: VmwareNetworkId):
    """Get information about a VMware network."""
    service_resp = asyncio.run(_network_service(ctx).get(network_id))
    echo(service_resp)


@network.command('create-isolated', cls=S2CTLCommand)
@output_option
@wait_option
@click.option('--location', type=int, required=True, help=_LOCATION_HELP)
@click.option('--name', required=True, help='Name of new network.')
@click.option('--address', required=True, help='Network address.')
@click.option(
    '--mask',
    type=int,
    help='The count of leading 1 bits in the routing mask '
    + '(e.g. 24 is equivalent to the 255.255.255.0).',
)
@click.option('--dhcp/--no-dhcp', 'enable_dhcp', default=False, show_default=True, help='Enable DHCP in the network.')
@click.pass_context
def create_isolated(
    ctx,
    location: VmwareLocationId,
    name: str,
    address: str,
    mask: Optional[int],
    enable_dhcp: bool,
    wait: bool,
):
    """Create new isolated network without access to the Internet."""
    service_resp = asyncio.run(_network_service(ctx).create_isolated(
        location_id=location,
        name=name,
        address=address,
        mask=mask,
        enable_dhcp=enable_dhcp,
        wait=wait,
    ))
    echo(service_resp)


@network.command('create-routed', cls=S2CTLCommand)
@output_option
@wait_option
@click.option('--location', type=int, required=True, help=_LOCATION_HELP)
@click.option('--name', required=True, help='Name of new network.')
@click.option('--address', required=True, help='Network address.')
@click.option(
    '--mask',
    type=int,
    help='The count of leading 1 bits in the routing mask '
    + '(e.g. 24 is equivalent to the 255.255.255.0).',
)
@click.option('--dhcp/--no-dhcp', 'enable_dhcp', default=False, show_default=True, help='Enable DHCP in the network.')
@click.option('--bandwidth', type=int, help='Bandwidth of the network edge gateway in Mbps.')
@click.pass_context
def create_routed(
    ctx,
    location: VmwareLocationId,
    name: str,
    address: str,
    mask: Optional[int],
    enable_dhcp: bool,
    bandwidth: Optional[int],
    wait: bool,
):
    """Create new routed network reaching the Internet through an edge gateway."""
    service_resp = asyncio.run(_network_service(ctx).create_routed(
        location_id=location,
        name=name,
        address=address,
        mask=mask,
        enable_dhcp=enable_dhcp,
        bandwidth_mbps=bandwidth,
        wait=wait,
    ))
    echo(service_resp)


@network.command('create-public', cls=S2CTLCommand)
@output_option
@wait_option
@click.option('--location', type=int, required=True, help=_LOCATION_HELP)
@click.option('--name', required=True, help='Name of new network.')
@click.option(
    '--capacity',
    type=click.Choice(_NETWORK_CAPACITIES, case_sensitive=False),
    required=True,
    help='Size of the public address block, named by its network prefix.',
)
@click.option('--bandwidth', type=int, help='Bandwidth of the network in Mbps.')
@click.pass_context
def create_public(ctx, location: VmwareLocationId, name: str, capacity: str, bandwidth: Optional[int], wait: bool):
    """Create new public network with a block of public addresses."""
    service_resp = asyncio.run(_network_service(ctx).create_public(
        location_id=location,
        name=name,
        capacity=capacity,
        bandwidth_mbps=bandwidth,
        wait=wait,
    ))
    echo(service_resp)


@network.command(cls=S2CTLCommand)
@output_option
@wait_option
@_network_id_argument
@click.option('--name', required=True, help='New name of the network.')
@click.pass_context
def rename(ctx, network_id: VmwareNetworkId, name: str, wait: bool):
    """Change the name of a VMware network."""
    network_service = _network_service(ctx)
    service_resp = asyncio.run(network_service.rename(network_id, name=name, wait=wait))
    echo(service_resp)


@network.command('set-bandwidth', cls=S2CTLCommand)
@output_option
@wait_option
@_network_id_argument
@click.option('--bandwidth', type=int, required=True, help='Bandwidth of the network in Mbps.')
@click.pass_context
def set_bandwidth(ctx, network_id: VmwareNetworkId, bandwidth: int, wait: bool):
    """Set the bandwidth of a routed or public VMware network."""
    service_resp = asyncio.run(_network_service(ctx).set_bandwidth(
        network_id, bandwidth_mbps=bandwidth, wait=wait,
    ))
    echo(service_resp)


@network.command(cls=S2CTLCommand)
@output_option
@wait_option
@_network_id_argument
@click.pass_context
def delete(ctx, network_id: VmwareNetworkId, wait: bool):
    """Delete a VMware network."""
    service_resp = asyncio.run(_network_service(ctx).delete(network_id, wait=wait))
    echo(service_resp)


@network.command('connect-servers', cls=S2CTLCommand)
@output_option
@wait_option
@_network_id_argument
@click.option(
    '--server',
    'nics',
    metavar='SERVER_ID[:IP]',
    multiple=True,
    required=True,
    callback=_parse_server_nics,
    help='Server to connect and the address to assign to its new interface. '
    + 'May be multiple. Without the address the interface gets it from the network.',
)
@click.option(
    '--force-customization',
    is_flag=True,
    help='Force guest customization of the connected servers.',
)
@click.pass_context
def connect_servers(
    ctx,
    network_id: VmwareNetworkId,
    nics: Sequence[VmwareServerNic],
    force_customization: bool,
    wait: bool,
):
    """Connect servers to a VMware network."""
    service_resp = asyncio.run(_network_service(ctx).connect_servers(
        network_id,
        nics=nics,
        force_customization=force_customization,
        wait=wait,
    ))
    echo(service_resp)


@vmware.group()
def edge():
    """Manage the edge gateway of a routed VMware network.

    The edge has no id of its own: commands take the id of the network it belongs to,
    as printed by "vmware network list".
    """


@edge.command('set-bandwidth', cls=S2CTLCommand)
@output_option
@wait_option
@_network_id_argument
@click.option('--bandwidth', type=int, required=True, help='Uplink bandwidth of the edge gateway in Mbps.')
@click.pass_context
def edge_set_bandwidth(ctx, network_id: VmwareNetworkId, bandwidth: int, wait: bool):
    """Set the uplink bandwidth of the edge gateway of a network.

    The value is checked against the bandwidth policy of the location. On a platform
    older than that check the task completes successfully while the bandwidth of the
    network keeps its previous value — there "s2ctl vmware network set-bandwidth"
    writes the same value instead.
    """
    service_resp = asyncio.run(_edge_service(ctx, network_id).set_bandwidth(
        bandwidth_mbps=bandwidth, wait=wait,
    ))
    echo(service_resp)


@edge.command('get-firewall', cls=S2CTLCommand)
@output_option
@_network_id_argument
@click.pass_context
def get_firewall(ctx, network_id: VmwareNetworkId):
    """Display the firewall of the edge gateway of a network."""
    service_resp = asyncio.run(_edge_service(ctx, network_id).firewall().get())
    echo(service_resp)


@edge.command('update-firewall', cls=S2CTLCommand)
@output_option
@wait_option
@rules_file_option
@_network_id_argument
@click.option(
    '--enabled/--disabled',
    default=None,
    help='Turn the firewall on or off. Omitted, it keeps its current state.',
)
@click.option(
    '--default-action',
    type=click.Choice(_FIREWALL_ACTIONS, case_sensitive=False),
    help='Action applied to the traffic matching no rule. Omitted, it keeps its current '
    + 'value — except on the first setup of the firewall, where there is nothing to keep '
    + 'and the API rejects the request without it.',
)
@click.pass_context
def update_firewall(
    ctx,
    network_id: VmwareNetworkId,
    rules: Sequence[Any],
    enabled: Optional[bool],
    default_action: Optional[str],
    wait: bool,
):
    """Replace the whole firewall rule set of the edge gateway of a network."""
    service_resp = asyncio.run(_edge_service(ctx, network_id).firewall().update(
        rules=rules,
        enabled=enabled,
        default_action=default_action,
        wait=wait,
    ))
    echo(service_resp)


@edge.command('get-nat', cls=S2CTLCommand)
@output_option
@_network_id_argument
@click.pass_context
def get_nat(ctx, network_id: VmwareNetworkId):
    """Display the NAT rules of the edge gateway of a network."""
    service_resp = asyncio.run(_edge_service(ctx, network_id).nat().get())
    echo(service_resp)


@edge.command('upsert-nat-rule', cls=S2CTLCommand)
@output_option
@wait_option
@_network_id_argument
@click.option('--rule-id', type=int, help='NAT rule to change. Without it a new rule is created.')
@click.option(
    '--type',
    'rule_type',
    type=click.Choice(_NAT_RULE_TYPES, case_sensitive=False),
    required=True,
    help='Translate the source ("SNAT") or the destination ("DNAT") of the traffic.',
)
@click.option(
    '--protocol',
    type=click.Choice(_PROTOCOLS, case_sensitive=False),
    required=True,
    help='Protocol the rule applies to.',
)
@click.option(
    '--original-ip',
    help='Original IP address. Required for a SNAT rule. Omitted, "any" goes to the API and '
    + 'the platform supplies the address: for a DNAT rule it always writes the external '
    + 'address of the edge gateway itself, whatever address is sent.',
)
@click.option('--original-port', help='Original port.')
@click.option(
    '--translated-ip',
    help='Translated IP address. Required for a DNAT rule. Omitted, "any" goes to the API and '
    + 'the platform supplies the address of the translation of a SNAT rule.',
)
@click.option('--translated-port', help='Translated port.')
@click.option('--description', help='Description of the rule.')
@click.option(
    '--enabled/--disabled',
    default=None,
    help='Whether the rule carries traffic. Omitted, an existing rule keeps the state it has '
    + 'and a new rule is created enabled.',
)
@click.pass_context
def upsert_nat_rule(
    ctx,
    network_id: VmwareNetworkId,
    rule_id: Optional[VmwareNatRuleId],
    rule_type: str,
    protocol: str,
    original_ip: Optional[str],
    original_port: Optional[str],
    translated_ip: Optional[str],
    translated_port: Optional[str],
    description: Optional[str],
    enabled: Optional[bool],
    wait: bool,
):
    """Create a NAT rule on the edge gateway of a network or change an existing one."""
    _check_rule_addresses(rule_type, original_ip, translated_ip)
    service_resp = asyncio.run(_edge_service(ctx, network_id).nat().upsert_rule(
        rule_id=rule_id,
        rule_type=rule_type,
        protocol=protocol,
        original_ip=original_ip,
        original_port=original_port,
        translated_ip=translated_ip,
        translated_port=translated_port,
        description=description,
        enabled=enabled,
        wait=wait,
    ))
    echo(service_resp)


@edge.command('delete-nat-rule', cls=S2CTLCommand)
@output_option
@wait_option
@_network_id_argument
@click.option('--rule-id', type=int, required=True, help='NAT rule identifier.')
@click.pass_context
def delete_nat_rule(ctx, network_id: VmwareNetworkId, rule_id: VmwareNatRuleId, wait: bool):
    """Delete a NAT rule of the edge gateway of a network."""
    nat_service = _edge_service(ctx, network_id).nat()
    service_resp = asyncio.run(nat_service.delete_rule(rule_id, wait=wait))
    echo(service_resp)


@edge.command('get-vpn', cls=S2CTLCommand)
@output_option
@_network_id_argument
@click.pass_context
def get_vpn(ctx, network_id: VmwareNetworkId):
    """Display the IPsec VPN tunnels of the edge gateway of a network."""
    service_resp = asyncio.run(_edge_service(ctx, network_id).vpn().get())
    echo(service_resp)


@edge.command('upsert-vpn-tunnel', cls=S2CTLCommand)
@output_option
@wait_option
@_network_id_argument
@click.option('--tunnel-id', type=int, help='VPN tunnel to change. Without it a new tunnel is created.')
@click.option('--name', required=True, help='Name of the tunnel.')
@click.option(
    '--shared-key',
    envvar='S2CTL_VPN_SHARED_KEY',
    prompt=True,
    hide_input=True,
    help='IPsec pre-shared key. Asked for interactively unless it is passed in '
    + 'S2CTL_VPN_SHARED_KEY: the command line lands in "ps", in the shell history '
    + 'and in the logs of a CI job.',
)
@click.option('--peer-network', required=True, help='Subnet of the remote side.')
@click.option('--peer-endpoint', required=True, help='Endpoint of the remote side.')
@click.option('--peer-identificator', required=True, help='Identifier of the remote side.')
@click.option('--mtu', type=int, required=True, help='MTU of the tunnel.')
@click.option(
    '--encryption-type',
    type=click.Choice(_VPN_ENCRYPTION_TYPES, case_sensitive=False),
    required=True,
    help='Encryption algorithm of the tunnel.',
)
@click.option(
    '--diffie-hellman-group',
    type=click.Choice(_DIFFIE_HELLMAN_GROUPS, case_sensitive=False),
    required=True,
    help='Diffie-Hellman group of the key exchange.',
)
@click.option(
    '--enabled/--disabled',
    default=None,
    help='Whether the tunnel carries traffic. Omitted, an existing tunnel keeps the state '
    + 'it has and a new tunnel is created enabled.',
)
@click.option(
    '--pfs/--no-pfs',
    'perfect_forward_secrecy',
    default=None,
    help='Whether Perfect Forward Secrecy is on. Omitted, an existing tunnel keeps the state '
    + 'it has and a new tunnel is created with it on.',
)
@click.pass_context
def upsert_vpn_tunnel(
    ctx,
    network_id: VmwareNetworkId,
    tunnel_id: Optional[VmwareVpnTunnelId],
    name: str,
    shared_key: str,
    peer_network: str,
    peer_endpoint: str,
    peer_identificator: str,
    mtu: int,
    encryption_type: str,
    diffie_hellman_group: str,
    enabled: Optional[bool],
    perfect_forward_secrecy: Optional[bool],
    wait: bool,
):
    """Create an IPsec VPN tunnel on the edge gateway of a network or change an existing one."""
    service_resp = asyncio.run(_edge_service(ctx, network_id).vpn().upsert_tunnel(
        tunnel_id=tunnel_id,
        name=name,
        shared_key=shared_key,
        peer_network=peer_network,
        peer_endpoint=peer_endpoint,
        peer_identificator=peer_identificator,
        mtu=mtu,
        encryption_type=encryption_type,
        diffie_hellman_group=diffie_hellman_group,
        enabled=enabled,
        perfect_forward_secrecy=perfect_forward_secrecy,
        wait=wait,
    ))
    echo(service_resp)


@edge.command('delete-vpn-tunnel', cls=S2CTLCommand)
@output_option
@wait_option
@_network_id_argument
@click.option('--tunnel-id', type=int, required=True, help='VPN tunnel identifier.')
@click.pass_context
def delete_vpn_tunnel(ctx, network_id: VmwareNetworkId, tunnel_id: VmwareVpnTunnelId, wait: bool):
    """Delete an IPsec VPN tunnel of the edge gateway of a network."""
    vpn_service = _edge_service(ctx, network_id).vpn()
    service_resp = asyncio.run(vpn_service.delete_tunnel(tunnel_id, wait=wait))
    echo(service_resp)
