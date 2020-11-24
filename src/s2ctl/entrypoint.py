import os
import types
from pathlib import Path

import click
from click.core import Context

from s2ctl.config import DEFAULT_CONFIG_PATH, ConfigManager
from s2ctl.context import ContextManager

CONTEXT_SETTINGS = types.MappingProxyType({'help_option_names': ['-h', '--help']})


def run_cli():
    entry_point()


def _get_config_manager(_ctx, _format, value: Path) -> ConfigManager:  # noqa: WPS110
    return ConfigManager(value)


@click.group(context_settings=CONTEXT_SETTINGS)
@click.option(
    '--config',
    '-c',
    'config_manager',
    type=click.types.Path(),
    default=DEFAULT_CONFIG_PATH,
    show_default=True,
    callback=_get_config_manager,
)
@click.option('--apikey', '-k', envvar='S2CTL_APIKEY')
@click.option('--debug', is_flag=True, hidden=True)
@click.pass_context
def entry_point(
    ctx: Context, config_manager: ConfigManager, apikey: str, debug: bool,
):
    ctx.ensure_object(dict)
    ctx.obj['config_manager'] = config_manager
    config = config_manager.get_config()
    keyring_path = config['keyring']
    keyring_key = os.environ.get('S2CTL_CONTEXT_KEY') or config.get('keyring_key', '')
    if not (keyring_key or apikey):
        ctx.exit(
            "Please set S2CTL_CONTEXT_KEY env variable or 'keyring_key' configuration value.\n"
            + 'Also you may set --apikey/S2CTL_APIKEY.',
        )

    context_maanger = ContextManager(
        config_manager=config_manager,
        keyring_key=keyring_key,
        keyring_path=keyring_path,
    )
    ctx.obj['keyring_pass_setted'] = bool(keyring_key)
    ctx.obj['context_manager'] = context_maanger
    ctx.obj['apikey_arg'] = apikey
    ctx.obj['debug'] = debug
