import click
import click_completion

from s2ctl.click import S2CTLCommand, echo
from s2ctl.entrypoint import entry_point


@entry_point.command(cls=S2CTLCommand)
@click.option('--append/--overwrite', help='Append the completion code to the file', default=None)
@click.option('-i', '--case-insensitive/--no-case-insensitive', help='Case insensitive completion')
@click.argument('shell', required=False, type=click_completion.DocumentedChoice(click_completion.shells))
@click.argument('path', required=False)
def install_autocomplete(append, case_insensitive, shell, path):
    """Install autocompletion"""
    if case_insensitive:
        extra_env = {'_CLICK_COMPLETION_COMMAND_CASE_INSENSITIVE_COMPLETE': 'ON'}
    else:
        extra_env = {}
    shell, path = click_completion.install(
        shell=shell, path=path, append=append, extra_env=extra_env,  # noqa: S604
    )
    echo('{shell} completion installed in {path}'.format(shell=shell, path=path))  # noqa: S604
