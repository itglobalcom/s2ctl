import asyncio
from typing import IO, Optional

import click
from click.core import Context

from s2ctl.click import S2CTLCommand, echo, output_option
from s2ctl.client import client_factory
from s2ctl.entrypoint import entry_point
from ssclient.sshkey import SshkeyService


def _get_sshkey_serivce(ctx: Context) -> SshkeyService:
    return ctx.obj['sshkeys_service']


@entry_point.group()
@click.pass_context
def ssh_key(ctx):
    """SSH keys management."""
    client = client_factory(ctx)
    ctx.obj['sshkeys_service'] = client.sshkeys()


@ssh_key.command(cls=S2CTLCommand)
@output_option
@click.option('--name', required=True, help='Name of new key.')
@click.option(
    '--public-key',
    help='Key value string in OpenSSH-compatible format '
    + '(starts with "ssh-rsa AAAA..." or "ssh-ed25519 AAAA...").',
)
@click.option(
    '--file',
    'sshkey_file',
    type=click.File('r'),
    help='Path to the file from which to read content of the key.',
)
@click.pass_context
def create(
    ctx,
    name: str,
    public_key: Optional[str],
    sshkey_file: Optional[IO],
):
    """Create new key."""
    if not (public_key or sshkey_file):
        click.echo('One the next options should be set: --public-key, --file', err=True)
        return

    if public_key and sshkey_file:
        click.echo("'--public-key' and '--file' can't be set at the same time")
        return

    sshkey_service = _get_sshkey_serivce(ctx)
    service_resp = asyncio.run(
        sshkey_service.create(
            name=name,
            public_key=public_key or sshkey_file.read(),
        ),
    )
    echo(service_resp)


@ssh_key.command('list', cls=S2CTLCommand)
@output_option
@click.pass_context
def list_ssh_key(ctx):
    """Display all SSH keys of the project."""
    sshkey_service = _get_sshkey_serivce(ctx)
    service_resp = asyncio.run(sshkey_service.list())
    echo(service_resp)


@ssh_key.command(cls=S2CTLCommand)
@output_option
@click.argument('sshkey-id', type=int, required=True)
@click.pass_context
def get(ctx, sshkey_id: int):
    """Get information about a key."""
    sshkey_service = _get_sshkey_serivce(ctx)
    service_resp = asyncio.run(
        sshkey_service.get(sshkey_id=sshkey_id),
    )
    echo(service_resp)


@ssh_key.command(cls=S2CTLCommand)
@output_option
@click.argument('sshkey-id', type=int, required=True)
@click.pass_context
def delete(ctx, sshkey_id: int):
    """Delete a key from project."""
    sshkey_service = _get_sshkey_serivce(ctx)
    service_resp = asyncio.run(
        sshkey_service.delete(sshkey_id=sshkey_id),
    )
    echo(service_resp)
