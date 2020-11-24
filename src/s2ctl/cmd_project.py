import asyncio

import click
from click.core import Context

from s2ctl.click import S2CTLCommand, echo, output_option
from s2ctl.client import client_factory
from s2ctl.entrypoint import entry_point
from ssclient.project import ProjectService


@entry_point.group()
@output_option
@click.pass_context
def project(ctx: Context):
    """Various actions related to projects — containers of anyother serverspace entities."""
    client = client_factory(ctx)
    ctx.obj['project_service'] = client.project()


def _get_proj_serivce(ctx) -> ProjectService:
    return ctx.obj['project_service']


@project.command(cls=S2CTLCommand)
@output_option
@click.pass_context
def show(ctx):
    """Display project information whose API key is bound to the current context."""
    proj_service = _get_proj_serivce(ctx)
    echo(asyncio.run(proj_service.get()))
