import types
from functools import wraps
from http import HTTPStatus
from typing import Any, Callable, Dict, Optional, cast

import click
import click_completion

from s2ctl.formatters import (
    FormatterPort,
    JSONFormatter,
    SorterType,
    TableFormatter,
    YAMLFormatter,
    general_fields_sort,
)
from ssclient.errors import HttpClientResponseError

FORMATTERS = types.MappingProxyType({
    'yaml': YAMLFormatter,
    'json': JSONFormatter,
    'table': TableFormatter,
})
FORMATTER_NAMES = tuple(FORMATTERS.keys())

click_completion.init()


def echo(
    raw_obj: Any,
    sorter: Optional[SorterType] = general_fields_sort,
    formatter: Optional[FormatterPort] = None,
    *args,
    **kwargs,
) -> None:
    ctx = click.get_current_context()
    if not formatter:
        formatter = cast(FormatterPort, ctx.obj['formatter'])

    if 'err' in kwargs:
        raise BaseFailException('\n{err_message}'.format(err_message=formatter.format(raw_obj)))
    elif raw_obj:
        click.echo(formatter.format(raw_obj, sorter), *args, **kwargs)


def wait_option(func):
    return click.option(
        '--wait',
        is_flag=True,
        help='wait for task to complete.',
    )(func)


def output_option(func):
    return click.option(
        '--output',
        '-o',
        type=click.Choice(FORMATTER_NAMES),
        default=FORMATTER_NAMES[0],
        show_default=True,
        expose_value=False,
        callback=_get_formatter,
    )(func)


def _get_formatter(ctx, _foramt, value) -> None:  # noqa: WPS110
    formatter = FORMATTERS.get(value)
    if not formatter:
        formatter = FORMATTERS[FORMATTER_NAMES[0]]
    ctx.obj['formatter'] = formatter()


def _command_callback_wrap(  # noqa: WPS231
    func: Callable[..., Any],
) -> Optional[Callable[..., Any]]:
    @wraps(func)
    def wrapper(*args, **kwargs):  # noqa: WPS430
        try:
            return func(*args, **kwargs)
        except BaseFailException:  # noqa: WPS329
            raise
        except HttpClientResponseError as exc:
            _check_http_response_error(exc)
        except Exception as exc:
            ctx = click.get_current_context()
            debug: bool = ctx.obj.get('debug')
            if debug:
                raise
            echo(exc, err=True)

    return wrapper


def _check_http_response_error(exc: HttpClientResponseError) -> None:
    if exc.status == HTTPStatus.UNAUTHORIZED:
        return echo("Can't log in. Check your API key.", err=True)
    elif exc.status == HTTPStatus.NOT_FOUND:
        return echo('object not found', err=True)
    return echo(exc.message, err=True)


class S2CTLCommand(click.Command):
    def __init__(
        self,
        name: str,
        context_settings: Optional[Dict[Any, Any]] = None,
        callback: Optional[Callable[..., Any]] = None,
        *args,
        **kwargs,
    ) -> None:
        if callback:
            callback = _command_callback_wrap(callback)
        super().__init__(name, context_settings, callback, *args, **kwargs)


class BaseFailException(click.ClickException):
    exit_code = -1
