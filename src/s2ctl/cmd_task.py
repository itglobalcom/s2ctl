import asyncio

import click
from click.core import Context

from s2ctl.click import S2CTLCommand, echo, output_option
from s2ctl.client import client_factory
from s2ctl.entrypoint import entry_point
from s2ctl.params import parse_task_id
from ssclient.task import TaskService
from ssclient.task_id import TaskId, supported_formats_hint

_GET_HELP = (
    'Get information about a task.'
    + '\n\n'
    + 'The prefix of the id says which service created the task: {formats}.'
).format(formats=supported_formats_hint())


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


@task.command(cls=S2CTLCommand, help=_GET_HELP)
@output_option
@click.argument('task_id', required=True, callback=parse_task_id)
@click.pass_context
def get(ctx, task_id: TaskId):
    task_service = _get_task_serivce(ctx)
    service_resp = asyncio.run(task_service.get(task_id=task_id))
    echo(service_resp)
