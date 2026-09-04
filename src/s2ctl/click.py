import types
from contextvars import ContextVar
from functools import wraps
from http import HTTPStatus
from typing import Any, Callable, Dict, Optional, Union, cast

import click

from s2ctl.formatters import (
    FormatterPort,
    JSONFormatter,
    SorterType,
    TableFormatter,
    YAMLFormatter,
    general_fields_sort,
)
from ssclient.errors import HttpClientResponseError, TaskWaitTimeoutError
from ssclient.task_wait import DEFAULT_TASK_TIMEOUT, TASK_TIMEOUT_SECS

# Признак отладки живёт в контексте вызова, а не в `ctx.obj`: перехват верхнего
# уровня работает и там, где контекста click ещё (или уже) нет.
DEBUG_MODE: ContextVar[bool] = ContextVar('debug_mode', default=False)

FORMATTERS = types.MappingProxyType({
    'yaml': YAMLFormatter,
    'json': JSONFormatter,
    'table': TableFormatter,
})
FORMATTER_NAMES = tuple(FORMATTERS.keys())

_OUTPUT_HELP = (
    'format of the printed result: yaml and json are machine-readable, for a script '
    + 'that parses the output; table is for reading by a human.'
)

_TIMEOUT_HELP = (
    'seconds to wait for the task, {default} by default; makes sense only together with --wait.'
).format(default=DEFAULT_TASK_TIMEOUT)

# Истёкшее ожидание задачу не отменяет: платформа применяет изменение дальше,
# поэтому отказ обязан назвать, чем задачу дождаться.
_TIMEOUT_MESSAGE = (
    '{reason}; the task is not canceled and goes on: '
    + 'check it with "s2ctl task get {task_id}" or wait longer with --timeout.'
)


def echo(
    raw_obj: Any,
    sorter: Optional[SorterType] = general_fields_sort,
    formatter: Optional[FormatterPort] = None,
    **kwargs,
) -> None:
    ctx = click.get_current_context()
    if not formatter:
        formatter = cast(FormatterPort, ctx.obj['formatter'])

    if 'err' in kwargs:
        raise BaseFailException('\n{err_message}'.format(err_message=formatter.format(raw_obj)))
    if raw_obj is None:
        # Операция без тела ответа: печатать нечего. Пустая коллекция от API — не этот
        # случай, её машинные форматы печатают документом (`[]`, `{}`), иначе скрипт
        # получает на разбор пустую строку.
        return
    printed = formatter.format(raw_obj, sorter)
    if printed:
        # `table` печатает пустой набор пустой строкой — таков вид пустоты у tabulate,
        # и перевод строки к нему не добавляется.
        click.echo(printed, **kwargs)


def wait_option(func):
    """`--wait` и парная к нему `--timeout`: ждать задачу и сколько её ждать."""
    func = click.option(
        '--timeout',
        type=click.IntRange(min=1),
        expose_value=False,
        callback=_set_task_timeout,
        help=_TIMEOUT_HELP,
    )(func)
    return click.option(
        '--wait',
        is_flag=True,
        # Eager: колбэк `--timeout` смотрит на `--wait`, а в `ctx.params` флаг
        # появляется только после того, как click обработал его параметр.
        is_eager=True,
        help='wait for task to complete.',
    )(func)


def _set_task_timeout(ctx, _timeout_param, raw_timeout: Optional[int]) -> None:
    if raw_timeout is None:
        return
    if not ctx.params.get('wait'):
        raise click.UsageError('--timeout makes sense only together with --wait')
    TASK_TIMEOUT_SECS.set(raw_timeout)


def output_option(func):
    return click.option(
        '--output',
        '-o',
        type=click.Choice(FORMATTER_NAMES),
        default=FORMATTER_NAMES[0],
        show_default=True,
        expose_value=False,
        callback=_get_formatter,
        help=_OUTPUT_HELP,
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
        except (HttpClientResponseError, TaskWaitTimeoutError) as exc:
            _report_expected_failure(exc)
        except Exception as exc:
            if DEBUG_MODE.get():
                raise
            # Текстом, а не объектом: `echo` отдаёт значение форматтеру вывода,
            # а исключение json-форматтер сериализовать не умеет — вторая ошибка
            # поверх первой ушла бы наружу трассировкой вместо сообщения.
            # `repr`, а не `str`: у неожиданного исключения тип и есть сообщение.
            echo(repr(exc), err=True)

    return wrapper


def _report_expected_failure(
    exc: Union[HttpClientResponseError, TaskWaitTimeoutError],
) -> None:
    """Ожидаемый исход операции: отказ API либо истёкшее ожидание задачи."""
    if isinstance(exc, TaskWaitTimeoutError):
        return _report_task_wait_timeout(exc)
    return _check_http_response_error(exc)


def _report_task_wait_timeout(exc: TaskWaitTimeoutError) -> None:
    echo(
        _TIMEOUT_MESSAGE.format(reason=exc, task_id=exc.task_id),
        err=True,
    )


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
        **kwargs,
    ) -> None:
        if callback:
            callback = _command_callback_wrap(callback)
        super().__init__(name, context_settings, callback, **kwargs)


class BaseFailException(click.ClickException):
    exit_code = -1
