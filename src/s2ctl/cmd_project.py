import asyncio

import click

from s2ctl.click import S2CTLCommand, echo, output_option
from s2ctl.client import client_factory
from s2ctl.entrypoint import entry_point
from ssclient.project import ProjectService


@entry_point.group()
@output_option
def project():
    """Various actions related to projects — containers of anyother serverspace entities."""


def _get_proj_serivce(ctx) -> ProjectService:
    return client_factory(ctx).project()


@project.command(cls=S2CTLCommand)
@output_option
@click.pass_context
def show(ctx):
    """Display project information whose API key is bound to the current context."""
    proj_service = _get_proj_serivce(ctx)
    echo(asyncio.run(proj_service.get()))
