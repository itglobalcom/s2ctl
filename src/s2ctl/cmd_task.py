import asyncio

import click
from click import Context

from s2ctl.click import S2CTLCommand, echo, output_option
from s2ctl.client import client_factory
from s2ctl.entrypoint import entry_point
from ssclient.task import TaskService


def _get_task_serivce(ctx: Context) -> TaskService:
    return ctx.obj['tasks_service']


@entry_point.group()
@click.pass_context
def task(ctx):
    """Many actions are long-running (e.g. creating a server) and
    executed in asynchronous way returning a task.
    """
    client = client_factory(ctx)
    ctx.obj['tasks_service'] = client.tasks()


@task.command(cls=S2CTLCommand)
@output_option
@click.argument('task_id', required=True)
@click.pass_context
def get(ctx, task_id: str):
    """Get information about a task."""
    task_service = _get_task_serivce(ctx)
    service_resp = asyncio.run(task_service.get(task_id=task_id))
    echo(service_resp)
