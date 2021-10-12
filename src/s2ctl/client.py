import types
from typing import Any, Dict, Optional

import click
from click.core import Context

from s2ctl.context import ContextManager
from ssclient.client import SSClient
from ssclient.http_client import HttpClient

HOSTS_MAP = types.MappingProxyType({
    '02': 'https://api.serverspace.by',
    '04': 'https://api.serverspace.io',
    '06': 'https://api.serverspace.ru',
    '07': 'https://api.lincore.kz',
    '08': 'https://api.serverspace.us',
    '09': 'https://api.serverspace.com.tr',
    '0a': 'https://api.serverspace.in',
})


def client_factory(ctx: Context) -> SSClient:
    context_manager: ContextManager = ctx.obj['context_manager']
    apikey_arg: str = ctx.obj['apikey_arg']
    try:
        apikey = apikey_arg or context_manager.get_current_apikey()
    except Exception:  # noqa: WPS329
        raise KeyMissingError

    if not apikey:
        raise KeyMissingError

    config: Dict[str, Any] = ctx.obj['config_manager'].get_config()
    host = config.get('host')
    if not host:
        host = get_host_by_apikey(apikey)
        if not host:
            raise WrongApikeyError

    return SSClient(HttpClient(host, apikey))


def get_host_by_apikey(apikey: str) -> Optional[str]:
    partner_code = apikey[:2].lower()
    return HOSTS_MAP.get(partner_code)


class KeyMissingError(click.UsageError):
    def __init__(self) -> None:
        super().__init__('You should setup apkey argument or select context')


class WrongApikeyError(click.UsageError):
    def __init__(self) -> None:
        super().__init__('Wrong apikey format')
