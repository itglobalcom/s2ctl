import asyncio
from typing import Optional

import click

from s2ctl.click import S2CTLCommand, echo, output_option
from s2ctl.client import client_factory
from s2ctl.entrypoint import entry_point


@entry_point.command(cls=S2CTLCommand)
@output_option
@click.pass_context
def locations(ctx):
    """List of places where our data centers are located.

    Every location carries the limits a server order is checked against:
    the minimum and the maximum volume size, the bandwidth range and the
    CPU and RAM values available for order.
    """
    client = client_factory(ctx)

    echo(asyncio.run(client.locations().get()))


@entry_point.command(cls=S2CTLCommand)
@output_option
@click.option('--location', help='Show only images of the location (see "locations" command).')
@click.pass_context
def images(ctx, location: Optional[str]):
    """List of OS images which you can use for your server.

    An image belongs to a single location ("location_id") and is offered
    in that location only.
    """
    client = client_factory(ctx)

    echo(asyncio.run(client.images().get(location_id=location)))


@entry_point.command(cls=S2CTLCommand)
@output_option
@click.option('--location', help='Show only applications of the location (see "locations" command).')
@click.option('--application', help='Show only the application with this identifier.')
@click.option('--image', help='Show only applications of the OS image (see "images" command).')
@click.pass_context
def applications(
    ctx, location: Optional[str], application: Optional[str], image: Optional[str],
):
    """List of applications which you can install on your server."""
    client = client_factory(ctx)
    applications_resp = asyncio.run(client.applications().list(
        location_id=location, application_id=application, image_id=image,
    ))

    echo(applications_resp)


@entry_point.command('backup-storages', cls=S2CTLCommand)
@output_option
@click.option('--location', required=True, help='Location of the server to order (see "locations" command).')
@click.option('--image', help='OS image of the server to order (see "images" command).')
@click.pass_context
def backup_storages(ctx, location: str, image: Optional[str]):
    """List of backup storages which you can choose for a new server.

    The limits of the backup schedule come along; the schedule itself is passed
    to "server create" with --backup-schedule-file.
    """
    storages_service = client_factory(ctx).backup_storages()

    echo(asyncio.run(storages_service.list(location_id=location, image_id=image)))
