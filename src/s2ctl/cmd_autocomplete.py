import os
import types
from pathlib import Path
from typing import NamedTuple, Optional

import click

from s2ctl.click import S2CTLCommand, echo, output_option
from s2ctl.entrypoint import entry_point

PROG_NAME = 's2ctl'
# Имя переменной задано click: он читает _<PROG_NAME>_COMPLETE, дефис в имени превращая в подчёркивание
COMPLETE_VAR = '_{prog}_COMPLETE'.format(prog=PROG_NAME.upper())


class ShellSetup(NamedTuple):
    startup_file: str
    source_line: str


# Стартовый файл — тот, что оболочка читает сама: у bash и zsh это rc-файл,
# у fish — каталог автозагрузки дополнений, где отдельная строка в конфиге не нужна.
SHELL_SETUPS = types.MappingProxyType({
    'bash': ShellSetup('~/.bashrc', 'eval "$({var}=bash_source {prog})"'),
    'zsh': ShellSetup('~/.zshrc', 'eval "$({var}=zsh_source {prog})"'),
    'fish': ShellSetup(
        '~/.config/fish/completions/{prog}.fish'.format(prog=PROG_NAME),
        '{var}=fish_source {prog} | source',
    ),
})
SHELL_NAMES = tuple(SHELL_SETUPS.keys())


@entry_point.command(cls=S2CTLCommand)
@output_option
@click.argument('shell', required=False, type=click.Choice(SHELL_NAMES))
@click.argument('path', required=False, type=click.types.Path(dir_okay=False))
def install_autocomplete(shell: Optional[str], path: Optional[str]) -> None:
    """Install autocompletion.

    SHELL defaults to the current one, PATH — to the startup file of that shell.
    """
    shell_name = shell or Path(os.environ.get('SHELL', '')).name
    shell_setup = SHELL_SETUPS.get(shell_name)
    if shell_setup is None:
        echo(
            'Unknown shell: {shell}. Supported shells: {shells}.'.format(
                shell=shell_name or '<not detected>',
                shells=', '.join(SHELL_NAMES),
            ),
            err=True,
        )
        return
    startup_file = Path(path or shell_setup.startup_file).expanduser()
    _add_source_line(startup_file, shell_setup.source_line.format(var=COMPLETE_VAR, prog=PROG_NAME))
    echo({'shell': shell_name, 'installed_in': str(startup_file)})


def _add_source_line(startup_file: Path, source_line: str) -> None:
    if startup_file.exists() and source_line in startup_file.read_text():
        return
    startup_file.parent.mkdir(parents=True, exist_ok=True)
    with startup_file.open('a') as startup_file_obj:
        startup_file_obj.write('\n{line}\n'.format(line=source_line))
