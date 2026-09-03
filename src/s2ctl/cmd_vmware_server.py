import asyncio
from typing import Any, Optional, Sequence

import click
from click.core import Context

from s2ctl.click import S2CTLCommand, echo, output_option, wait_option
from s2ctl.cmd_vmware import vmware, vmware_service
from s2ctl.params import rules_file_option
from ssclient.vmware.firewall import VmwareServerFirewallService
from ssclient.vmware.power import VmwareServerPowerService
from ssclient.vmware.server import VmwareServerService
from ssclient.vmware.server_entities import VmwareServerGpu, VmwareServerOrder

SERVER_ID_ARG = 'server-id'

_LOCATION_HELP = 'Location identifier (see "vmware locations" command).'
_IMAGE_HELP = 'OS template identifier (see "vmware images" command).'
_GPU_HINT = 'gpu format: MODEL_ID:VRAM_MB:CARD_COUNT, e.g. "3:8192:1"'
_GPU_PARTS_COUNT = 3


def _parse_gpu(_ctx, _click_param, raw_gpu: Optional[str]) -> Optional[VmwareServerGpu]:
    if raw_gpu is None:
        return None
    parts = raw_gpu.split(':')
    is_triple = len(parts) == _GPU_PARTS_COUNT
    if not is_triple or not all(part.isdigit() for part in parts):
        raise click.BadParameter(_GPU_HINT)
    model_id, vram_mb, card_count = [int(part) for part in parts]
    return VmwareServerGpu(gpu_model_id=model_id, vram_mb=vram_mb, card_count=card_count)


_ORDER_OPTIONS = (
    click.option('--location', type=int, required=True, help=_LOCATION_HELP),
    click.option('--name', required=True, help='Display name of the server.'),
    click.option(
        '--computer-name',
        help='Hostname of the guest OS. Omitted, the platform derives one from the name.',
    ),
    click.option('--image', type=int, required=True, help=_IMAGE_HELP),
    click.option('--cpu', type=int, required=True, help='Number of cores.'),
    click.option('--ram', type=int, required=True, help='Amount of RAM in MB.'),
    click.option('--system-disk-size', type=int, required=True, help='Size of the system disk in MB.'),
    click.option(
        '--system-disk-type',
        help='Type of the system disk, by title, as offered by the location '
        + '(see "disk_types" in "vmware locations").',
    ),
    click.option('--public-network', type=int, help='Public network to connect the server to.'),
    click.option(
        '--bandwidth',
        type=int,
        help='Bandwidth of the public interface in Mbps. With --public-network the interface '
        + 'takes the bandwidth of that network instead.',
    ),
    click.option(
        '--backup/--no-backup',
        'backup_enabled',
        default=False,
        show_default=True,
        help='Enable backups of the server.',
    ),
    click.option('--backup-period', type=int, help='Period of backups in days.'),
    click.option(
        '--ssh-key',
        'ssh_keys',
        type=int,
        multiple=True,
        help='Identifier of a SSH key to inject into a Linux image (see "ssh-key" command). May be multiple.',
    ),
    click.option('--sysprep', 'need_sysprep', is_flag=True, help='Run sysprep for a Windows image.'),
    click.option(
        '--nested-hypervisor',
        is_flag=True,
        help='Create the server with nested virtualization on (see "nested_hypervisor_supported" '
        + 'in "vmware locations").',
    ),
    click.option(
        '--gpu',
        metavar='MODEL_ID:VRAM_MB:CARD_COUNT',
        callback=_parse_gpu,
        help='GPU profile of the server. The platform picks the slicing policy by the whole '
        + 'triple at once, so all three values are named together (see "vmware gpu-models" command).',
    ),
)


def _server_service(ctx: Context) -> VmwareServerService:
    return vmware_service(ctx).servers()


def _power_service(ctx: Context, server_id: int) -> VmwareServerPowerService:
    return _server_service(ctx).power(server_id)


def _firewall_service(ctx: Context, server_id: int) -> VmwareServerFirewallService:
    return _server_service(ctx).firewall(server_id)


def _server_id_argument(func):
    return click.argument(SERVER_ID_ARG, required=True, type=int)(func)


def _order_options(command):
    decorated = command
    for add_option in reversed(_ORDER_OPTIONS):
        decorated = add_option(decorated)
    return decorated


# WPS211: состав заказа задан формой запроса контракта — разбирается он целиком.
def _order(  # noqa: WPS211
    *,
    location: int,
    name: str,
    computer_name: Optional[str],
    image: int,
    cpu: int,
    ram: int,
    system_disk_size: int,
    system_disk_type: Optional[str],
    public_network: Optional[int],
    bandwidth: Optional[int],
    backup_enabled: bool,
    backup_period: Optional[int],
    ssh_keys: Sequence[int],
    need_sysprep: bool,
    nested_hypervisor: bool,
    gpu: Optional[VmwareServerGpu],
) -> VmwareServerOrder:
    return VmwareServerOrder(
        location_id=location,
        name=name,
        computer_name=computer_name,
        image_id=image,
        cpu_count=cpu,
        ram_mb=ram,
        system_disk_size_mb=system_disk_size,
        system_disk_type=system_disk_type,
        public_network_id=public_network,
        network_bandwidth_mbps=bandwidth,
        backup_enabled=backup_enabled,
        backup_period=backup_period,
        ssh_keys=ssh_keys,
        need_sysprep=need_sysprep,
        nested_hypervisor=nested_hypervisor,
        gpu=gpu,
    )


@vmware.group()
def server():
    """Manage VMware servers."""


@server.command('list', cls=S2CTLCommand)
@output_option
@click.option('--location', type=int, help='Show only servers of the location.')
@click.pass_context
def servers_list(ctx, location: Optional[int]):
    """Display all VMware servers in the project."""
    service_resp = asyncio.run(_server_service(ctx).list(location_id=location))
    echo(service_resp)


@server.command(cls=S2CTLCommand)
@output_option
@_server_id_argument
@click.pass_context
def get(ctx, server_id: int):
    """Get information about a VMware server."""
    service_resp = asyncio.run(_server_service(ctx).get(server_id))
    echo(service_resp)


@server.command(cls=S2CTLCommand)
@output_option
@wait_option
@_order_options
@click.pass_context
def create(ctx, wait: bool, **order_fields):
    """Order a new VMware server."""
    server_service = _server_service(ctx)
    service_resp = asyncio.run(server_service.create(_order(**order_fields), wait=wait))
    echo(service_resp)


@server.command(cls=S2CTLCommand)
@output_option
@_order_options
@click.pass_context
def verify(ctx, **order_fields):
    """Check the parameters of a server order without ordering the server."""
    service_resp = asyncio.run(_server_service(ctx).verify(_order(**order_fields)))
    echo(service_resp)


@server.command('set-configuration', cls=S2CTLCommand)
@output_option
@wait_option
@_server_id_argument
@click.option('--cpu', type=int, required=True, help='Number of cores.')
@click.option('--ram', type=int, required=True, help='Amount of RAM in MB.')
@click.option('--system-disk-size', type=int, required=True, help='Size of the system disk in MB.')
@click.pass_context
def set_configuration(ctx, server_id: int, cpu: int, ram: int, system_disk_size: int, wait: bool):
    """Change the cores, the memory and the system disk of a VMware server."""
    service_resp = asyncio.run(_server_service(ctx).set_configuration(
        server_id,
        cpu=cpu,
        ram_mb=ram,
        system_disk_size_mb=system_disk_size,
        wait=wait,
    ))
    echo(service_resp)


@server.command(cls=S2CTLCommand)
@output_option
@_server_id_argument
@click.option('--name', required=True, help='New display name of the server.')
@click.pass_context
def rename(ctx, server_id: int, name: str):
    """Change the display name of a VMware server."""
    service_resp = asyncio.run(_server_service(ctx).rename(server_id, name=name))
    echo(service_resp)


@server.command('set-computer-name', cls=S2CTLCommand)
@output_option
@wait_option
@_server_id_argument
@click.option('--computer-name', required=True, help='New hostname of the guest OS.')
@click.option(
    '--force-customization',
    is_flag=True,
    help='Force guest customization of the server.',
)
@click.pass_context
def set_computer_name(ctx, server_id: int, computer_name: str, force_customization: bool, wait: bool):
    """Change the guest OS hostname of a VMware server."""
    service_resp = asyncio.run(_server_service(ctx).set_computer_name(
        server_id,
        computer_name=computer_name,
        force_customization=force_customization,
        wait=wait,
    ))
    echo(service_resp)


@server.command(cls=S2CTLCommand)
@output_option
@wait_option
@_server_id_argument
@click.option('--name', required=True, help='Name of the copy.')
@click.option('--client-network', type=int, help='Client network to connect the copy to.')
@click.pass_context
def copy(ctx, server_id: int, name: str, client_network: Optional[int], wait: bool):
    """Create a copy of a VMware server."""
    service_resp = asyncio.run(_server_service(ctx).copy(
        server_id,
        name=name,
        client_network_id=client_network,
        wait=wait,
    ))
    echo(service_resp)


@server.command(cls=S2CTLCommand)
@output_option
@wait_option
@_server_id_argument
@click.option('--image', type=int, required=True, help=_IMAGE_HELP)
@click.option('--sysprep', 'need_sysprep', is_flag=True, help='Run sysprep for a Windows image.')
@click.pass_context
def rebuild(ctx, server_id: int, image: int, need_sysprep: bool, wait: bool):
    """Recreate a VMware server from an OS template as a new server with a new identifier."""
    service_resp = asyncio.run(_server_service(ctx).rebuild(
        server_id,
        image_id=image,
        need_sysprep=need_sysprep,
        wait=wait,
    ))
    echo(service_resp)


@server.command(cls=S2CTLCommand)
@output_option
@wait_option
@_server_id_argument
@click.pass_context
def delete(ctx, server_id: int, wait: bool):
    """Delete a VMware server."""
    service_resp = asyncio.run(_server_service(ctx).delete(server_id, wait=wait))
    echo(service_resp)


@server.command('enable-nested-hypervisor', cls=S2CTLCommand)
@output_option
@wait_option
@_server_id_argument
@click.pass_context
def enable_nested_hypervisor(ctx, server_id: int, wait: bool):
    """Turn nested virtualization on for a VMware server."""
    server_service = _server_service(ctx)
    service_resp = asyncio.run(server_service.enable_nested_hypervisor(server_id, wait=wait))
    echo(service_resp)


@server.command('disable-nested-hypervisor', cls=S2CTLCommand)
@output_option
@wait_option
@_server_id_argument
@click.pass_context
def disable_nested_hypervisor(ctx, server_id: int, wait: bool):
    """Turn nested virtualization off for a VMware server."""
    server_service = _server_service(ctx)
    service_resp = asyncio.run(server_service.disable_nested_hypervisor(server_id, wait=wait))
    echo(service_resp)


@server.command('power-on', cls=S2CTLCommand)
@output_option
@wait_option
@_server_id_argument
@click.pass_context
def power_on(ctx, server_id: int, wait: bool):
    """Power a VMware server on."""
    service_resp = asyncio.run(_power_service(ctx, server_id).power_on(wait=wait))
    echo(service_resp)


@server.command('power-off', cls=S2CTLCommand)
@output_option
@wait_option
@_server_id_argument
@click.pass_context
def power_off(ctx, server_id: int, wait: bool):
    """Cut the power of a VMware server without shutting the guest OS down."""
    service_resp = asyncio.run(_power_service(ctx, server_id).power_off(wait=wait))
    echo(service_resp)


@server.command(cls=S2CTLCommand)
@output_option
@wait_option
@_server_id_argument
@click.pass_context
def shutdown(ctx, server_id: int, wait: bool):
    """Shut the guest OS of a VMware server down through VMware Tools."""
    service_resp = asyncio.run(_power_service(ctx, server_id).shutdown(wait=wait))
    echo(service_resp)


@server.command(cls=S2CTLCommand)
@output_option
@wait_option
@_server_id_argument
@click.pass_context
def reboot(ctx, server_id: int, wait: bool):
    """Reboot the guest OS of a VMware server through VMware Tools."""
    service_resp = asyncio.run(_power_service(ctx, server_id).reboot(wait=wait))
    echo(service_resp)


@server.command(cls=S2CTLCommand)
@output_option
@wait_option
@_server_id_argument
@click.pass_context
def reset(ctx, server_id: int, wait: bool):
    """Restart a VMware server without shutting the guest OS down."""
    service_resp = asyncio.run(_power_service(ctx, server_id).reset(wait=wait))
    echo(service_resp)


@server.command('get-firewall', cls=S2CTLCommand)
@output_option
@_server_id_argument
@click.pass_context
def get_firewall(ctx, server_id: int):
    """Display the firewall rules of a VMware server."""
    service_resp = asyncio.run(_firewall_service(ctx, server_id).get())
    echo(service_resp)


@server.command('update-firewall', cls=S2CTLCommand)
@output_option
@wait_option
@rules_file_option
@_server_id_argument
@click.pass_context
def update_firewall(ctx, server_id: int, rules: Sequence[Any], wait: bool):
    """Replace the whole firewall rule set of a VMware server."""
    firewall_service = _firewall_service(ctx, server_id)
    service_resp = asyncio.run(firewall_service.update(rules=rules, wait=wait))
    echo(service_resp)
