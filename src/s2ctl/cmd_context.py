
import click
from click.core import Context

from s2ctl.click import S2CTLCommand, echo, output_option
from s2ctl.context import ContextManager
from s2ctl.entrypoint import entry_point


@entry_point.group()
@click.pass_context
def context(ctx: Context):
    """Contexts are used for accessing concrete projects.
    You may have more than one context to control several projects.
    """
    if not ctx.obj['keyring_pass_setted']:
        ctx.exit(
            "You must set S2CTL_CONTEXT_KEY (or 'keyring_key' configuration value) "
            + 'to be able to perform operations on contexts.',
        )


def _get_context_manager(ctx) -> ContextManager:
    return ctx.obj['context_manager']


@context.command(cls=S2CTLCommand)
@output_option
@click.option('--name', '-n', required=True, help='Name of a context.')
@click.option('--key', '-k', required=True, help='API key obtained from control panel.')
@click.pass_context
def create(ctx, name: str, key: str):
    """Create new context with API key obtained from control panel."""
    context_manager = _get_context_manager(ctx)
    try:
        context_manager.add_context(context_name=name, apikey=key)
    except Exception as exc:
        echo(exc, err=True)


@context.command(cls=S2CTLCommand)
@output_option
@click.argument('name')
@click.pass_context
def select(ctx, name: str):
    """Make chosen context active. All executed actions will be perfomed
    in context of project whose API key is bound to the selected context.
    """
    context_manager = _get_context_manager(ctx)
    try:
        context_manager.set_context(name)
    except Exception as exc:
        echo(exc, err=True)


@context.command('list', cls=S2CTLCommand)
@output_option
@click.pass_context
def contexts_list(ctx):
    """List of all created contexts."""
    context_manager = _get_context_manager(ctx)
    try:
        echo(context_manager.contexts_list())
    except Exception as exc:
        echo(exc, err=True)


@context.command(cls=S2CTLCommand)
@output_option
@click.pass_context
def show(ctx):
    """Display which context is active."""
    context_manager = _get_context_manager(ctx)
    try:
        echo({
            'active_context': context_manager.get_current_context_name(),
        })
    except Exception as exc:
        echo(exc, err=True)


@context.command(cls=S2CTLCommand)
@output_option
@click.argument('name')
@click.pass_context
def delete(ctx, name: str):
    """Delete context."""
    context_manager = _get_context_manager(ctx)
    try:
        context_manager.delete_context(name)
    except Exception as exc:
        echo(exc, err=True)
