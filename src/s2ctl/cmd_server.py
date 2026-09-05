import asyncio
import string
from typing import Any, Dict, List, Optional, Sequence

import click
from click.core import Context

from s2ctl.click import S2CTLCommand, echo, output_option, wait_option
from s2ctl.client import client_factory
from s2ctl.entrypoint import entry_point
from s2ctl.formatters import general_fields_sort
from s2ctl.params import parse_network_id, parse_server_id
from ssclient.network.network_id import NetworkId
from ssclient.server.server import ServerService, VolumeCreationData
from ssclient.server.server_id import SERVER_ID_TEMPLATE, ServerId

SERVER_ID_ARG = 'server-id'

_GROUP_HELP = (
    'Manage virtual servers inside your project.'
    + '\n\n'
    + 'Commands take the server id in the {template} format, as printed by "list".'
).format(template=SERVER_ID_TEMPLATE)

_SERVER_FIELDS_ORDER = (
    'id',
    'name',
    'state',
    'created',
    'is_power_on',
    'image_id',
    'location_id',
    'cpu',
    'ram_mb',
    'volumes',
    'nics',
    'login',
    'password',
    'ssh_key_ids',
)


class VolumeType(click.types.ParamType[VolumeCreationData]):
    name = '<(NAME:)SIZE{M|G}>'

    def convert(self, value: Any, param, ctx) -> VolumeCreationData:  # noqa: WPS110
        splitted_value = value.rsplit(':', 1)
        if len(splitted_value) == 1:
            name = 'boot'
            size = splitted_value[0]
        elif len(splitted_value) == 2:
            name = str(splitted_value[0])
            size = splitted_value[1]
        else:
            self.fail('it would appear that format of value is wrong', param, ctx)

        size = SizeType().convert(size, param, ctx)
        return VolumeCreationData(name, size)


class SizeType(click.types.ParamType[int]):
    name = '<INT{M|G}>'

    def convert(self, value: Any, param, ctx) -> int:  # noqa: WPS110
        if value:
            suffix = value[-1].lower()
        else:
            suffix = ''

        if suffix in string.digits:
            suffix = 'm'
            size = int(value)
        elif suffix in {'m', 'g'}:
            size = int(value[:-1])
        else:
            self.fail(
                '{suffix} wrong size suffix (available only m, g)'.format(suffix=suffix), param, ctx,
            )

        if suffix == 'g':
            size *= 1024
        return size


def _get_server_serivce(ctx: Context) -> ServerService:
    return client_factory(ctx).servers()


def sort_server_resp(resp: Dict[str, Any]) -> Dict[str, Any]:
    return general_fields_sort(resp, fields_order=_SERVER_FIELDS_ORDER)


@entry_point.group(help=_GROUP_HELP)
def server():
    """Manage virtual servers inside your project."""


@server.command(cls=S2CTLCommand)
@output_option
@wait_option
@click.option('--name', required=True, help='Name of new server.')
@click.option('--location', required=True, help='Where to create a server (see "locations" command).')
@click.option('--image', required=True, help='OS images which you want to use for new server.')
@click.option('--cpu', required=True, help='CPU cores count.')
@click.option('--ram', type=SizeType(), required=True, help='RAM size (e.g. 1024, 1024M or 1G for 1Gb of RAM).')
@click.option(
    '--volume',
    'volumes',
    type=VolumeType(),
    required=True,
    multiple=True,
    help='Volume size in form VolumeName:VolumeSize. May be multiple. The first specified volume becomes '
    + 'system (boot) and its name is ignored. Therefore it can be skipped. E.g. "--volume 10240 --volume '
    + 'Second:30G" will create a server with 10Gb system (boot) volume and 30Gb volume named "Second". '
    + 'The allowed sizes depend on the location: see "system_volume_min", "windows_system_volume_min", '
    + '"additional_volume_min" and "volume_max" of the "locations" command.',
)
@click.option(
    '--public-network',
    'public_networks',
    type=int,
    required=True,
    multiple=True,
    help='Bandwidth of the public network interface in Mbps. '
    + 'May be multiple to create several interfaces with appropriate bandwidths.',
)
@click.option(
    '--ssh-key',
    'ssh_key_ids',
    type=int,
    required=False,
    multiple=True,
    help='Identifier of a SSH key which you want to use to access a server (see "ssh-key" command). May be multiple.',
)
@click.pass_context
def create(
    ctx,
    name: str,
    location: str,
    image: str,
    cpu: int,
    ram: int,
    volumes: Sequence[VolumeCreationData],
    public_networks: Sequence[int],
    ssh_key_ids: List[int],
    wait: bool,
):
    """Create new virtual server."""
    server_service = _get_server_serivce(ctx)
    service_resp = asyncio.run(
        server_service.create(
            name=name,
            location_id=location,
            image_id=image,
            cpu=cpu,
            ram_mb=ram,
            volumes=volumes,
            networks=public_networks,
            ssh_key_ids=ssh_key_ids,
            wait=wait,
        ),
    )
    echo(service_resp, sorter=sort_server_resp)


@server.command(cls=S2CTLCommand)
@output_option
@wait_option
@click.argument(SERVER_ID_ARG, required=True, callback=parse_server_id)
@click.option('--cpu', help='CPU cores count.')
@click.option(
    '--ram',
    type=SizeType(),
    help='RAM size (e.g. 1024, 1024M or 1G for 1Gb of RAM).',
)
@click.pass_context
def edit(ctx, server_id: ServerId, cpu: Optional[int], ram: Optional[int], wait: bool):
    """Change only the specified parameters of a server configuration."""
    server_service = _get_server_serivce(ctx)
    service_resp = asyncio.run(
        server_service.update(server_id=server_id, cpu=cpu, ram_mb=ram, wait=wait),
    )
    echo(service_resp)


@server.command('set-configuration', cls=S2CTLCommand)
@output_option
@wait_option
@click.argument(SERVER_ID_ARG, required=True, callback=parse_server_id)
@click.option('--cpu', type=int, required=True, help='CPU cores count.')
@click.option(
    '--ram',
    type=SizeType(),
    required=True,
    help='RAM size (e.g. 1024, 1024M or 1G for 1Gb of RAM).',
)
@click.pass_context
def set_configuration(ctx, server_id: ServerId, cpu: int, ram: int, wait: bool):
    """Set the whole server configuration: both CPU cores count and RAM size."""
    server_service = _get_server_serivce(ctx)
    service_resp = asyncio.run(
        server_service.set_configuration(server_id=server_id, cpu=cpu, ram_mb=ram, wait=wait),
    )
    echo(service_resp, sorter=sort_server_resp)


@server.command(cls=S2CTLCommand)
@output_option
@wait_option
@click.argument(SERVER_ID_ARG, required=True, callback=parse_server_id)
@click.option('--name', required=True, help='New name of the server.')
@click.pass_context
def rename(ctx, server_id: ServerId, name: str, wait: bool):
    """Change the name of a server."""
    server_service = _get_server_serivce(ctx)
    service_resp = asyncio.run(
        server_service.rename(server_id=server_id, name=name, wait=wait),
    )
    echo(service_resp, sorter=sort_server_resp)


@server.command(cls=S2CTLCommand)
@output_option
@click.option('--location', required=True, help='Where the server is priced (see "locations" command).')
@click.option('--image', required=True, help='OS image which you want to use for the server.')
@click.option('--cpu', type=int, required=True, help='CPU cores count.')
@click.option('--ram', type=SizeType(), required=True, help='RAM size (e.g. 1024, 1024M or 1G for 1Gb of RAM).')
@click.option(
    '--volume',
    'volumes',
    type=SizeType(),
    required=True,
    multiple=True,
    help='Volume size (e.g. 10240, 1024M or 10G for 10Gb volume). May be multiple. '
    + 'The first specified volume becomes system (boot). The allowed sizes depend on the location: '
    + 'see "system_volume_min", "additional_volume_min" and "volume_max" of the "locations" command.',
)
@click.option(
    '--public-network',
    'public_networks',
    type=int,
    multiple=True,
    help='Bandwidth of the public network interface in Mbps. May be multiple. '
    + 'If omitted, one interface with the minimal bandwidth of the location is priced.',
)
@click.pass_context
def price(
    ctx,
    location: str,
    image: str,
    cpu: int,
    ram: int,
    volumes: Sequence[int],
    public_networks: Sequence[int],
):
    """Get the monthly price of a server configuration."""
    price_service = _get_server_serivce(ctx).prices()
    service_resp = asyncio.run(
        price_service.calculate(
            location_id=location,
            image_id=image,
            cpu=cpu,
            ram_mb=ram,
            volumes=volumes,
            networks=public_networks,
        ),
    )
    echo(service_resp)


@server.command('list', cls=S2CTLCommand)
@output_option
@click.pass_context
def servers_list(ctx):
    """Display all virtual servers in the project."""
    server_service = _get_server_serivce(ctx)
    service_resp = asyncio.run(server_service.list())
    echo(service_resp, sorter=sort_server_resp)


@server.command(cls=S2CTLCommand)
@output_option
@click.argument(SERVER_ID_ARG, required=True, callback=parse_server_id)
@click.pass_context
def get(ctx, server_id: ServerId):
    """Get information about a server."""
    server_service = _get_server_serivce(ctx)
    service_resp = asyncio.run(server_service.get(server_id=server_id))
    echo(service_resp, sorter=sort_server_resp)


@server.command(cls=S2CTLCommand)
@output_option
@wait_option
@click.argument(SERVER_ID_ARG, required=True, callback=parse_server_id)
@click.pass_context
def delete(ctx, server_id: ServerId, wait: bool):
    """Delete a server."""
    server_service = _get_server_serivce(ctx)
    service_resp = asyncio.run(server_service.delete(server_id=server_id, wait=wait))
    echo(service_resp, sorter=sort_server_resp)


@server.command(cls=S2CTLCommand)
@output_option
@wait_option
@click.argument(SERVER_ID_ARG, required=True, callback=parse_server_id)
@click.option('--volume-name', required=True, help='Name of new volume.')
@click.option(
    '--volume-size',
    type=SizeType(),
    required=True,
    help='Size of new volume (e.g. 10240, 1024M or 10G for 10Gb volume). The allowed sizes depend on the '
    + 'location of the server: see "additional_volume_min" and "volume_max" of the "locations" command.',
)
@click.pass_context
def add_volume(ctx, server_id: ServerId, volume_name: str, volume_size: int, wait: bool):
    """Add new storage volume to a server."""
    server_service = _get_server_serivce(ctx)
    volume_service = server_service.volumes(server_id=server_id)
    service_resp = asyncio.run(
        volume_service.create(name=volume_name, size_mb=volume_size, wait=wait),
    )
    echo(service_resp)


@server.command(cls=S2CTLCommand)
@output_option
@wait_option
@click.argument(SERVER_ID_ARG, required=True, callback=parse_server_id)
@click.option('--volume-id', type=int, required=True, help='Volume identifier.')
@click.option(
    '--volume-size',
    type=SizeType(),
    required=True,
    help='New size of the volume (e.g. 20480, 20480M or 20G for 20Gb volume). '
    + 'Must be greater than current.',
)
@click.option(
    '--volume-name',
    help='New name of the volume. Omitted, the name is kept.',
)
@click.pass_context
def edit_volume(
    ctx, server_id: ServerId, volume_id: int, volume_size: int, volume_name: Optional[str], wait: bool,
):
    """Change the size and the name of a storage volume."""
    server_service = _get_server_serivce(ctx)
    volume_service = server_service.volumes(server_id=server_id)
    service_resp = asyncio.run(
        volume_service.update(
            volume_id=volume_id, size_mb=volume_size, name=volume_name, wait=wait,
        ),
    )
    echo(service_resp)


@server.command(cls=S2CTLCommand)
@output_option
@click.argument(SERVER_ID_ARG, required=True, callback=parse_server_id)
@click.option('--volume-id', type=int, required=True, help='Volume identifier.')
@click.pass_context
def get_volume(ctx, server_id: ServerId, volume_id: int):
    """Get information about a storage volume."""
    server_service = _get_server_serivce(ctx)
    volume_service = server_service.volumes(server_id=server_id)
    service_resp = asyncio.run(
        volume_service.get(volume_id=volume_id),
    )
    echo(service_resp)


@server.command(cls=S2CTLCommand)
@output_option
@click.argument(SERVER_ID_ARG, required=True, callback=parse_server_id)
@click.pass_context
def list_volume(ctx, server_id: ServerId):
    """Display all storage volumes of a server."""
    server_service = _get_server_serivce(ctx)
    volume_service = server_service.volumes(server_id=server_id)
    service_resp = asyncio.run(volume_service.list())
    echo(service_resp)


@server.command(cls=S2CTLCommand)
@output_option
@wait_option
@click.argument(SERVER_ID_ARG, required=True, callback=parse_server_id)
@click.option('--volume-id', type=int, required=True, help='Volume identifier.')
@click.pass_context
def delete_volume(ctx, server_id: ServerId, volume_id: int, wait: bool):
    """Remove a storage volume from a server."""
    server_service = _get_server_serivce(ctx)
    volume_service = server_service.volumes(server_id=server_id)
    service_resp = asyncio.run(
        volume_service.delete(volume_id=volume_id, wait=wait),
    )
    echo(service_resp)


@server.command(cls=S2CTLCommand)
@output_option
@wait_option
@click.argument(SERVER_ID_ARG, required=True, callback=parse_server_id)
@click.option(
    '--network-id',
    type=str,
    required=False,
    callback=parse_network_id,
    help='Network identifier (see "network" command).',
)
@click.option(
    '--bandwidth',
    type=int,
    required=False,
    help='Public network interface bandwidth. '
    + 'Interface bandwidth in Mbps, the bandwidth value must be a multiple of 10 Mbps.',
)
@click.pass_context
def add_nic(
    ctx, server_id: ServerId, network_id: Optional[NetworkId], bandwidth: Optional[int], wait: bool,
):
    """
    Add new network interface to a server.

    Only one of the following parameters can be specified: `network_id` and `bandwidth`!
    If you pass both the parameters you get an error.
    Pass `network_id` if you need to connect to isolated network. If you need to connect
    to public network pass `bandwidth`.
    """
    if network_id and bandwidth:
        raise ExclusiveOptionsError(['network-id', 'bandwidth'])

    server_service = _get_server_serivce(ctx)
    nic_service = server_service.nics(server_id=server_id)
    service_resp = asyncio.run(
        nic_service.create(network_id=network_id, bandwidth=bandwidth, wait=wait),
    )
    echo(service_resp)


@server.command(cls=S2CTLCommand)
@output_option
@click.argument(SERVER_ID_ARG, required=True, callback=parse_server_id)
@click.pass_context
def list_nic(ctx, server_id: ServerId):
    """Display all network interfaces of a server."""
    server_service = _get_server_serivce(ctx)
    nic_service = server_service.nics(server_id=server_id)
    service_resp = asyncio.run(nic_service.list())
    echo(service_resp)


@server.command(cls=S2CTLCommand)
@output_option
@click.argument(SERVER_ID_ARG, required=True, callback=parse_server_id)
@click.option('--nic-id', type=int, required=True, help='Network interface identifier.')
@click.pass_context
def get_nic(ctx, server_id: ServerId, nic_id: int):
    """Get information about a network interface."""
    server_service = _get_server_serivce(ctx)
    nic_service = server_service.nics(server_id=server_id)
    service_resp = asyncio.run(
        nic_service.get(nic_id=nic_id),
    )
    echo(service_resp)


@server.command(cls=S2CTLCommand)
@output_option
@wait_option
@click.argument(SERVER_ID_ARG, required=True, callback=parse_server_id)
@click.option('--nic-id', type=int, required=True, help='Network interface identifier.')
@click.option(
    '--bandwidth',
    type=int,
    required=True,
    help='New public network interface bandwidth in Mbps, must be a multiple of 10 Mbps.',
)
@click.pass_context
def edit_nic(ctx, server_id: ServerId, nic_id: int, bandwidth: int, wait: bool):
    """Change bandwidth of a network interface."""
    server_service = _get_server_serivce(ctx)
    nic_service = server_service.nics(server_id=server_id)
    service_resp = asyncio.run(
        nic_service.update(nic_id=nic_id, bandwidth_mbps=bandwidth, wait=wait),
    )
    echo(service_resp)


@server.command(cls=S2CTLCommand)
@output_option
@wait_option
@click.argument(SERVER_ID_ARG, required=True, callback=parse_server_id)
@click.option('--nic-id', type=int, required=True, help='Network interface identifier.')
@click.pass_context
def delete_nic(ctx, server_id: ServerId, nic_id: int, wait: bool):
    """Remove a network interface from a server."""
    server_service = _get_server_serivce(ctx)
    nic_service = server_service.nics(server_id=server_id)
    service_resp = asyncio.run(nic_service.delete(nic_id=nic_id, wait=wait))
    echo(service_resp)


@server.command(cls=S2CTLCommand)
@output_option
@wait_option
@click.argument(SERVER_ID_ARG, required=True, callback=parse_server_id)
@click.pass_context
def power_on(ctx, server_id: ServerId, wait: bool):
    """Power a server on."""
    power_service = _get_server_serivce(ctx).power(server_id=server_id)
    service_resp = asyncio.run(power_service.power_on(wait=wait))
    echo(service_resp)


@server.command(cls=S2CTLCommand)
@output_option
@wait_option
@click.argument(SERVER_ID_ARG, required=True, callback=parse_server_id)
@click.pass_context
def power_off(ctx, server_id: ServerId, wait: bool):
    """Cut the power of a server without shutting its operating system down."""
    power_service = _get_server_serivce(ctx).power(server_id=server_id)
    service_resp = asyncio.run(power_service.power_off(wait=wait))
    echo(service_resp)


@server.command(cls=S2CTLCommand)
@output_option
@wait_option
@click.argument(SERVER_ID_ARG, required=True, callback=parse_server_id)
@click.pass_context
def shutdown(ctx, server_id: ServerId, wait: bool):
    """Shut a server down through its operating system."""
    power_service = _get_server_serivce(ctx).power(server_id=server_id)
    service_resp = asyncio.run(power_service.shutdown(wait=wait))
    echo(service_resp)


@server.command(cls=S2CTLCommand)
@output_option
@wait_option
@click.argument(SERVER_ID_ARG, required=True, callback=parse_server_id)
@click.pass_context
def reboot(ctx, server_id: ServerId, wait: bool):
    """Reboot a server through its operating system."""
    power_service = _get_server_serivce(ctx).power(server_id=server_id)
    service_resp = asyncio.run(power_service.reboot(wait=wait))
    echo(service_resp)


@server.command(cls=S2CTLCommand)
@output_option
@wait_option
@click.argument(SERVER_ID_ARG, required=True, callback=parse_server_id)
@click.pass_context
def reset(ctx, server_id: ServerId, wait: bool):
    """Reset a server by power, without asking its operating system."""
    power_service = _get_server_serivce(ctx).power(server_id=server_id)
    service_resp = asyncio.run(power_service.reset(wait=wait))
    echo(service_resp)


@server.command(cls=S2CTLCommand)
@output_option
@wait_option
@click.argument(SERVER_ID_ARG, required=True, callback=parse_server_id)
@click.option('--name', required=True, help='Name of the snapshot.')
@click.pass_context
def create_snapshot(ctx, server_id: ServerId, name: str, wait: bool):
    """Create snapshot of a server."""
    server_service = _get_server_serivce(ctx)
    snapshot_service = server_service.snapshots(server_id=server_id)
    service_resp = asyncio.run(snapshot_service.create(name=name, wait=wait))
    echo(service_resp)


@server.command(cls=S2CTLCommand)
@output_option
@click.argument(SERVER_ID_ARG, required=True, callback=parse_server_id)
@click.pass_context
def list_snapshot(ctx, server_id: ServerId):
    """Display all snapshots of a server."""
    server_service = _get_server_serivce(ctx)
    snapshot_service = server_service.snapshots(server_id=server_id)
    service_resp = asyncio.run(snapshot_service.list())
    echo(service_resp)


@server.command(cls=S2CTLCommand)
@output_option
@click.argument(SERVER_ID_ARG, required=True, callback=parse_server_id)
@click.option('--snapshot-id', type=int, required=True, help='Snapshot identifier.')
@click.pass_context
def get_snapshot(ctx, server_id: ServerId, snapshot_id: int):
    """Get information about a snapshot of a server."""
    server_service = _get_server_serivce(ctx)
    snapshot_service = server_service.snapshots(server_id=server_id)
    service_resp = asyncio.run(
        snapshot_service.get(snapshot_id=snapshot_id),
    )
    echo(service_resp)


@server.command(cls=S2CTLCommand)
@output_option
@wait_option
@click.argument(SERVER_ID_ARG, required=True, callback=parse_server_id)
@click.option('--snapshot-id', type=int, required=True, help='Snapshot identifier.')
@click.pass_context
def rollback_snapshot(ctx, server_id: ServerId, snapshot_id: int, wait: bool):
    """Rollback a server to a saved snapshot."""
    server_service = _get_server_serivce(ctx)
    snapshot_service = server_service.snapshots(server_id=server_id)
    service_resp = asyncio.run(
        snapshot_service.rollback(snapshot_id=snapshot_id, wait=wait),
    )
    echo(service_resp)


@server.command(cls=S2CTLCommand)
@output_option
@wait_option
@click.argument(SERVER_ID_ARG, required=True, callback=parse_server_id)
@click.option('--snapshot-id', type=int, required=True, help='Snapshot identifier.')
@click.pass_context
def delete_snapshot(ctx, server_id: ServerId, snapshot_id: int, wait: bool):
    """Remove a snapshot of a server."""
    server_service = _get_server_serivce(ctx)
    snapshot_service = server_service.snapshots(server_id=server_id)
    service_resp = asyncio.run(
        snapshot_service.delete(snapshot_id=snapshot_id, wait=wait),
    )
    echo(service_resp)


@server.command(cls=S2CTLCommand)
@output_option
@click.argument(SERVER_ID_ARG, required=True, callback=parse_server_id)
@click.option('--name', required=True, help='Name of tag.')
@click.pass_context
def add_tag(ctx, server_id: ServerId, name: str):
    """Add tag to server."""
    server_service = _get_server_serivce(ctx)
    tag_service = server_service.tags(server_id=server_id)
    service_resp = asyncio.run(tag_service.create(name=name))
    echo(service_resp)


@server.command(cls=S2CTLCommand)
@output_option
@click.argument(SERVER_ID_ARG, required=True, callback=parse_server_id)
@click.option('--name', type=str, required=True, help='Name of tag.')
@click.pass_context
def delete_tag(ctx, server_id: ServerId, name: str):
    """Remove tag from server."""
    server_service = _get_server_serivce(ctx)
    tag_service = server_service.tags(server_id=server_id)
    service_resp = asyncio.run(
        tag_service.delete(name=name),
    )
    echo(service_resp)


class ExclusiveOptionsError(click.UsageError):
    def __init__(
        self,
        exclusive_fields: List[str],
    ) -> None:
        msg = 'Only one exclusive field can be set at a time: {exclusive_fields}'.format(
            exclusive_fields=exclusive_fields,
        )
        super().__init__(msg)
