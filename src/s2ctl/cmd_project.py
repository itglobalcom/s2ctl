import asyncio
import datetime
from typing import Optional

import click

from s2ctl.click import S2CTLCommand, echo, output_option
from s2ctl.client import client_factory
from s2ctl.entrypoint import entry_point
from s2ctl.params import period_options
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


@project.command(cls=S2CTLCommand)
@output_option
@period_options
@click.pass_context
def consumption(
    ctx, period_from: Optional[datetime.date], period_to: Optional[datetime.date],
):
    """Spending of the project by service over a period.

    "is_final" is false while the period reaches today: the day is still being charged.
    """
    proj_service = _get_proj_serivce(ctx)
    consumption_resp = proj_service.consumption(period_from, period_to)
    echo(asyncio.run(consumption_resp))


@project.command('consumption-resources', cls=S2CTLCommand)
@output_option
@period_options
@click.option(
    '--service',
    help='Show only the resources of the service, the value of "service" in the output (vstack, vmware, …).',
)
@click.pass_context
def consumption_resources(
    ctx,
    period_from: Optional[datetime.date],
    period_to: Optional[datetime.date],
    service: Optional[str],
):
    """Spending of the project by root resource over a period.

    "id" is present when the resource is addressable by the API, "name" when it is known.
    """
    proj_service = _get_proj_serivce(ctx)
    consumption_resp = proj_service.consumption_resources(period_from, period_to, service)
    echo(asyncio.run(consumption_resp))


@project.command('consumption-daily', cls=S2CTLCommand)
@output_option
@period_options
@click.pass_context
def consumption_daily(
    ctx, period_from: Optional[datetime.date], period_to: Optional[datetime.date],
):
    """Spending of the project day by day over a period, days without charges included."""
    proj_service = _get_proj_serivce(ctx)
    consumption_resp = proj_service.consumption_daily(period_from, period_to)
    echo(asyncio.run(consumption_resp))
