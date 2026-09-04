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
    """List of places where our data centers are located."""
    client = client_factory(ctx)
    locations_resp = asyncio.run(client.locations().get())

    echo(list({location['id'] for location in locations_resp}))


@entry_point.command(cls=S2CTLCommand)
@output_option
@click.pass_context
def images(ctx):
    """List of OS images which you can use for your server."""
    client = client_factory(ctx)
    images_resp = asyncio.run(client.images().get())

    echo(list({image['id'] for image in images_resp}))


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
    applications_resp = asyncio.run(client.applications().get(
        location_id=location, application_id=application, image_id=image,
    ))

    echo(applications_resp)
