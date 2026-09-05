import asyncio
from types import MappingProxyType
from typing import Any, Dict, Iterable, Mapping

import click

from s2ctl.click import S2CTLCommand, echo, output_option, wait_option
from s2ctl.client import client_factory
from s2ctl.entrypoint import entry_point
from ssclient.domain import record_entities as entities
from ssclient.domain.domain import DomainService

# Опция команды → поле тела записи у publisher'а: имена совпадают всюду, кроме
# канонического имени, которое в CLI короче.
_RECORD_FIELD_BY_OPTION: Mapping[str, str] = MappingProxyType({
    'ip': 'ip',
    'cname': 'canonical_name',
    'mail_host': 'mail_host',
    'name_server_host': 'name_server_host',
    'text': 'text',
    'protocol': 'protocol',
    'service': 'service',
    'weight': 'weight',
    'port': 'port',
    'target': 'target',
    'priority': 'priority',
})

_OPTION_BY_RECORD_FIELD: Mapping[str, str] = MappingProxyType({
    record_field: option for option, record_field in _RECORD_FIELD_BY_OPTION.items()
})

_RECORD_OPTIONS = (
    click.option('--name', required=True, help='Name of the resource.'),
    click.option(
        '--ttl',
        type=click.Choice(entities.AllowedTTLType.list()),
        callback=lambda _ctx, _format, value: entities.AllowedTTLType(value),  # noqa: WPS110
        required=True,
        help='Count of seconds that the record stays valid.',
    ),
    click.option(
        '--type',
        'record_type',
        type=click.Choice(entities.AllowedRecordType.list(), case_sensitive=False),
        callback=lambda _ctx, _format, value: entities.AllowedRecordType(value.lower()),  # noqa: WPS110,E501
        required=True,
        help='Type of the record.',
    ),
    click.option('--ip', help='IP address of the host.'),
    click.option('--cname', help='Canonical name of the domain.'),
    click.option(
        '--mail-host',
        help='Host name of mail exchange servers accepting incoming mail for that domain.',
    ),
    click.option(
        '--name-server-host',
        help='Name server host.',
    ),
    click.option(
        '--text',
        help='Some text information (using in txt records).',
    ),
    click.option(
        '--service',
        type=str,
        help='Symbolic name of the desired service.',
    ),
    click.option(
        '--protocol',
        type=str,
        help='Transport protocol of the desired service (such as TCP, UDP).',
    ),
    click.option(
        '--weight',
        type=int,
        help='Relative weight for records with the same priority. '
        + 'Higher value means higher chance of getting picked.',
    ),
    click.option(
        '--port',
        type=int,
        help='TCP or UDP port on which the service is to be found.',
    ),
    click.option(
        '--target',
        type=str,
        help='Canonical hostname of the machine providing the service, ending in a dot.',
    ),
    click.option(
        '--priority',
        type=int,
        help='Just an int value. Behavior depends on record type. '
        + 'Usually lower value means more preferred',
    ),
)

_RECORD_ID_OPTION = click.option(
    '--record-id',
    'record_id',
    type=int,
    required=True,
    help='Record id.',
)


def _record_options(command):
    """Опции записи: состав тела задаёт тип записи, и он общий у создания и правки."""
    for option in reversed(_RECORD_OPTIONS):
        command = option(command)
    return command


def _get_domain_serivce(ctx) -> DomainService:
    return client_factory(ctx).domains()


def _option_flag(option: str) -> str:
    return '--{option}'.format(option=option.replace('_', '-'))


def _record_fields(given_options: Dict[str, Any]) -> Dict[str, entities.RecordFieldValue]:
    """Поля тела записи из опций, которые пользователь задал.

    Заданное отличается от незаданного наличием значения, а не истинностью: нулевой
    `priority` записи MX и нулевые `weight` и `port` записи SRV — штатные значения,
    и publisher требует их непустыми (`[EncodedRequired]`).
    """
    return {
        record_field: given_options[option]
        for option, record_field in _RECORD_FIELD_BY_OPTION.items()
        if given_options.get(option) is not None
    }


def check_allowed_fields(
    record_type: entities.AllowedRecordType,
    record_fields: Mapping[str, entities.RecordFieldValue],
) -> None:
    """Отказывает, если набор полей не тот, что нужен записи этого типа."""
    expected = entities.record_type_fields(record_type)
    given = frozenset(record_fields)
    if given == expected:
        return
    raise WrongFieldSetGetted(
        record_type=record_type.value,
        necessary_fields=sorted(expected - given),
        extra_fields=sorted(given - expected),
    )


@entry_point.group()
def domain():
    """Manage dns domains and records.

    Commands address a domain by its own name, as printed by "list" (e.g. "example.com"),
    and a record inside it by "--record-id" — the plain integer printed by "list-record".
    """


@domain.command(cls=S2CTLCommand)
@output_option
@wait_option
@click.option('--name', required=True, help='Name of creating domain.')
@click.option(
    '--migrate-records',
    is_flag=True,
    default=False,
    show_default=True,
    help='Migrate dns records from outer world.',
)
@click.pass_context
def create(
    ctx,
    name: str,
    migrate_records: bool,
    wait: bool,
):
    """Create new domain."""
    domain_service = _get_domain_serivce(ctx)
    service_resp = asyncio.run(domain_service.create(
        name=name,
        migrate_records=migrate_records,
        wait=wait,
    ))
    echo(service_resp)


@domain.command('list', cls=S2CTLCommand)
@output_option
@click.pass_context
def list_domain(ctx):
    """Display all domains in the project."""
    domain_service = _get_domain_serivce(ctx)
    service_resp = asyncio.run(domain_service.list())
    echo(service_resp)


@domain.command(cls=S2CTLCommand)
@output_option
@click.argument('domain-name', required=True)
@click.pass_context
def get(ctx, domain_name: str):
    """Get domain information."""
    domain_service = _get_domain_serivce(ctx)
    service_resp = asyncio.run(domain_service.get(domain_name=domain_name))
    echo(service_resp)


@domain.command(cls=S2CTLCommand)
@output_option
@wait_option
@click.argument('domain-name', required=True)
@click.pass_context
def delete(ctx, domain_name: str, wait: bool):
    """Delete a domain."""
    domain_service = _get_domain_serivce(ctx)
    service_resp = asyncio.run(domain_service.delete(domain_name=domain_name, wait=wait))
    echo(service_resp)


@domain.command(cls=S2CTLCommand)
@output_option
@wait_option
@click.argument('domain-name', required=True)
@_record_options
@click.pass_context
def create_record(
    ctx,
    domain_name: str,
    name: str,
    ttl: entities.AllowedTTLType,
    record_type: entities.AllowedRecordType,
    wait: bool,
    **given_options,
):
    """Create new record."""
    record_fields = _record_fields(given_options)
    check_allowed_fields(record_type, record_fields)
    record_service = _get_domain_serivce(ctx).records(domain_name=domain_name)
    service_resp = asyncio.run(record_service.create(
        name=name,
        record_type=record_type,
        ttl=ttl,
        fields=record_fields,
        wait=wait,
    ))
    echo(service_resp)


@domain.command(cls=S2CTLCommand)
@output_option
@wait_option
@click.argument('domain-name', required=True)
@_RECORD_ID_OPTION
@_record_options
@click.pass_context
def update_record(
    ctx,
    domain_name: str,
    record_id: int,
    name: str,
    ttl: entities.AllowedTTLType,
    record_type: entities.AllowedRecordType,
    wait: bool,
    **given_options,
):
    """Replace the record with the given one."""
    record_fields = _record_fields(given_options)
    check_allowed_fields(record_type, record_fields)
    record_service = _get_domain_serivce(ctx).records(domain_name=domain_name)
    service_resp = asyncio.run(record_service.update(
        record_id=record_id,
        name=name,
        record_type=record_type,
        ttl=ttl,
        fields=record_fields,
        wait=wait,
    ))
    echo(service_resp)


@domain.command(cls=S2CTLCommand)
@output_option
@click.argument('domain-name', required=True)
@click.pass_context
def list_record(ctx, domain_name: str):
    """Display all records in the domain."""
    domain_service = _get_domain_serivce(ctx)
    record_service = domain_service.records(domain_name=domain_name)
    service_resp = asyncio.run(record_service.list())
    echo(service_resp)


@domain.command(cls=S2CTLCommand)
@output_option
@click.argument('domain-name', required=True)
@_RECORD_ID_OPTION
@click.pass_context
def get_record(ctx, domain_name: str, record_id: int):
    """Get record information."""
    domain_service = _get_domain_serivce(ctx)
    record_service = domain_service.records(domain_name=domain_name)
    service_resp = asyncio.run(record_service.get(record_id=record_id))
    echo(service_resp)


@domain.command(cls=S2CTLCommand)
@output_option
@wait_option
@click.argument('domain-name', required=True)
@_RECORD_ID_OPTION
@click.pass_context
def delete_record(ctx, domain_name: str, record_id: int, wait: bool):
    """Remove the record from a domain."""
    domain_service = _get_domain_serivce(ctx)
    record_service = domain_service.records(domain_name=domain_name)
    service_resp = asyncio.run(
        record_service.delete(record_id=record_id, wait=wait),
    )
    echo(service_resp)


class WrongFieldSetGetted(click.UsageError):
    def __init__(
        self,
        record_type: str,
        necessary_fields: Iterable[str],
        extra_fields: Iterable[str],
    ) -> None:
        msg = 'Wrong set of fields for {record_type}.'.format(record_type=record_type)
        if necessary_fields:
            msg += ' Necessary options {nec_field}'.format(
                nec_field=', '.join(_option_flag(_OPTION_BY_RECORD_FIELD[field])
                                    for field in necessary_fields),
            )
        if extra_fields:
            msg += ' Extra options {extra_fields}'.format(
                extra_fields=', '.join(_option_flag(_OPTION_BY_RECORD_FIELD[field])
                                       for field in extra_fields),
            )
        super().__init__(msg)
