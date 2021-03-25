import asyncio
from typing import Iterable, Optional

import click

from s2ctl.click import S2CTLCommand, echo, output_option, wait_option
from s2ctl.client import client_factory
from s2ctl.entrypoint import entry_point
from ssclient.domain import record_entities as entities
from ssclient.domain.domain import DomainService


def _get_domain_serivce(ctx) -> DomainService:
    return ctx.obj['domain_service']


@entry_point.group()
@click.pass_context
def domain(ctx):
    """Manage dns domains and records."""
    client = client_factory(ctx)
    ctx.obj['domain_service'] = client.domains()


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
@click.argument('domain-name', required=True)
@click.pass_context
def delete(ctx, domain_name: str):
    """Delete a domain."""
    domain_service = _get_domain_serivce(ctx)
    service_resp = asyncio.run(domain_service.delete(domain_name=domain_name))
    echo(service_resp)


@domain.command(cls=S2CTLCommand)
@output_option
@wait_option
@click.argument('domain-name', required=True)
@click.option('--name', required=True, help='Name of the resource.')
@click.option(
    '--ttl',
    type=click.Choice(entities.AllowedTTLType.list()),
    callback=lambda _ctx, _format, value: entities.AllowedTTLType(value),  # noqa: WPS110
    required=True,
    help='Count of seconds that the record stays valid.',
)
@click.option(
    '--type',
    'record_type',
    type=click.Choice(entities.AllowedRecordType.list(), case_sensitive=False),
    callback=lambda _ctx, _format, value: entities.AllowedRecordType(value.lower()),  # noqa: WPS110
    required=True,
    help='Type of the record.',
)
@click.option('--ip', help='IP address of the host.')
@click.option('--cname', help='Canonical name of the domain.')
@click.option(
    '--mail-host',
    help='Host name of mail exchange servers accepting incoming mail for that domain.',
)
@click.option(
    '--name-server-host',
    help='Name server host.',
)
@click.option(
    '--text',
    help='Some text information (using in txt records).',
)
@click.option(
    '--service',
    type=str,
    help='Symbolic name of the desired service.',
)
@click.option(
    '--protocol',
    type=str,
    help='Transport protocol of the desired service (such as TCP, UDP).',
)
@click.option(
    '--weight',
    type=int,
    help='Relative weight for records with the same priority. '
    + 'Higher value means higher chance of getting picked.',
)
@click.option(
    '--port',
    type=int,
    help='TCP or UDP port on which the service is to be found.',
)
@click.option(
    '--target',
    type=str,
    help='Canonical hostname of the machine providing the service, ending in a dot.',
)
@click.option(
    '--priority',
    type=int,
    help='Just an int value. Behavior depends on record type. '
    + 'Usually lower value means more preferred',
)
@click.pass_context
def create_record(  # noqa: WPS231
    ctx,
    domain_name: str,
    name: str,
    ttl: entities.AllowedTTLType,
    record_type: entities.AllowedRecordType,
    ip: Optional[str],
    cname: Optional[str],
    mail_host: Optional[str],
    name_server_host: Optional[str],
    text: Optional[str],
    protocol: Optional[str],
    service: Optional[str],
    weight: Optional[int],
    port: Optional[int],
    target: Optional[str],
    priority: Optional[int],
    wait: bool,
):
    """Create new record."""
    domain_service = _get_domain_serivce(ctx)
    record_service = domain_service.records(domain_name=domain_name)
    check_allowed_fields(
        record_type=record_type,
        ip=ip,
        cname=cname,
        mail_host=mail_host,
        name_server_host=name_server_host,
        text=text,
        protocol=protocol,
        service=service,
        weight=weight,
        port=port,
        target=target,
        priority=priority,
    )
    if record_type == entities.AllowedRecordType.a:  # noqa: WPS223
        service_resp = asyncio.run(record_service.create_a(
            name=name,
            ttl=ttl,
            ip=ip,  # type: ignore
            wait=wait,
        ))
    elif record_type == entities.AllowedRecordType.aaaa:
        service_resp = asyncio.run(record_service.create_aaaa(
            name=name,
            ttl=ttl,
            ip=ip,  # type: ignore
            wait=wait,
        ))
    elif record_type == entities.AllowedRecordType.cname:
        service_resp = asyncio.run(record_service.create_cname(
            name=name,
            ttl=ttl,
            canonical_name=cname,  # type: ignore
            wait=wait,
        ))
    elif record_type == entities.AllowedRecordType.mx:
        service_resp = asyncio.run(record_service.create_mx(
            name=name,
            ttl=ttl,
            mail_host=mail_host,  # type: ignore
            priority=priority,  # type: ignore
            wait=wait,
        ))
    elif record_type == entities.AllowedRecordType.ns:
        service_resp = asyncio.run(record_service.create_ns(
            name=name,
            ttl=ttl,
            name_server_host=name_server_host,  # type: ignore
            wait=wait,
        ))
    elif record_type == entities.AllowedRecordType.txt:
        service_resp = asyncio.run(record_service.create_txt(
            name=name,
            ttl=ttl,
            text=text,  # type: ignore
            wait=wait,
        ))
    elif record_type == entities.AllowedRecordType.srv:
        service_resp = asyncio.run(record_service.create_srv(
            name=name,
            ttl=ttl,
            protocol=protocol,  # type: ignore
            service=service,  # type: ignore
            weight=weight,  # type: ignore
            port=port,  # type: ignore
            target=target,  # type: ignore
            priority=priority,  # type: ignore
            wait=wait,
        ))
    else:
        raise WrongRecordType

    echo(service_resp)


@domain.command(cls=S2CTLCommand)
@output_option
@wait_option
@click.argument('domain-name', required=True)
@click.option(
    '--record-id',
    'record_id',
    type=int,
    required=True,
    help='Record id.',
)
@click.option('--name', required=True, help='Name of the resource.')
@click.option(
    '--ttl',
    type=click.Choice(entities.AllowedTTLType.list()),
    callback=lambda _ctx, _format, value: entities.AllowedTTLType(value),  # noqa: WPS110
    required=True,
    help='Count of seconds that the record stays valid.',
)
@click.option(
    '--type',
    'record_type',
    type=click.Choice(entities.AllowedRecordType.list(), case_sensitive=False),
    callback=lambda _ctx, _format, value: entities.AllowedRecordType(value.lower()),  # noqa: WPS110
    required=True,
    help='Type of the record.',
)
@click.option('--ip', help='IP address of the host.')
@click.option('--cname', help='Canonical name of the domain.')
@click.option(
    '--mail-host',
    help='Host name of mail exchange servers accepting incoming mail for that domain.',
)
@click.option(
    '--name-server-host',
    help='Name server host.',
)
@click.option(
    '--text',
    help='Some text information (using in txt records).',
)
@click.option(
    '--service',
    type=str,
    help='Symbolic name of the desired service.',
)
@click.option(
    '--protocol',
    type=str,
    help='Transport protocol of the desired service (such as TCP, UDP).',
)
@click.option(
    '--weight',
    type=int,
    help='Relative weight for records with the same priority. '
    + 'Higher value means higher chance of getting picked.',
)
@click.option(
    '--port',
    type=int,
    help='TCP or UDP port on which the service is to be found.',
)
@click.option(
    '--target',
    type=str,
    help='Canonical hostname of the machine providing the service, ending in a dot.',
)
@click.option(
    '--priority',
    type=int,
    help='Just an int value. Behavior depends on record type. '
    + 'Usually lower value means more preferred',
)
@click.pass_context
def update_record(  # noqa: WPS231
    ctx,
    domain_name: str,
    record_id: int,
    name: str,
    ttl: entities.AllowedTTLType,
    record_type: entities.AllowedRecordType,
    ip: Optional[str],
    cname: Optional[str],
    mail_host: Optional[str],
    name_server_host: Optional[str],
    text: Optional[str],
    protocol: Optional[str],
    service: Optional[str],
    weight: Optional[int],
    port: Optional[int],
    target: Optional[str],
    priority: Optional[int],
    wait: bool,
):
    """Create new record."""
    domain_service = _get_domain_serivce(ctx)
    record_service = domain_service.records(domain_name=domain_name)
    check_allowed_fields(
        record_type=record_type,
        ip=ip,
        cname=cname,
        mail_host=mail_host,
        name_server_host=name_server_host,
        text=text,
        protocol=protocol,
        service=service,
        weight=weight,
        port=port,
        target=target,
        priority=priority,
    )
    service_resp = asyncio.run(record_service.update(
        record_id=record_id,
        name=name,
        ttl=ttl,
        record_type=record_type,
        ip=ip,
        cname=cname,
        mail_host=mail_host,
        name_server_host=name_server_host,
        text=text,
        protocol=protocol,
        service=service,
        weight=weight,
        port=port,
        target=target,
        priority=priority,
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
@click.option(
    '--record-id',
    'record_id',
    type=int,
    required=True,
    help='Record id.',
)
@click.pass_context
def get_record(ctx, domain_name: str, record_id: int):
    """Get record information."""
    domain_service = _get_domain_serivce(ctx)
    record_service = domain_service.records(domain_name=domain_name)
    service_resp = asyncio.run(record_service.get(record_id=record_id))
    echo(service_resp)


@domain.command(cls=S2CTLCommand)
@output_option
@click.argument('domain-name', required=True)
@click.option(
    '--record-id',
    'record_id',
    type=int,
    required=True,
    help='Record id.',
)
@click.pass_context
def delete_record(ctx, domain_name: str, record_id: int):
    """Remove the record from a domain."""
    domain_service = _get_domain_serivce(ctx)
    record_service = domain_service.records(domain_name=domain_name)
    service_resp = asyncio.run(
        record_service.delete(record_id=record_id),
    )
    echo(service_resp)


def check_allowed_fields(  # noqa: WPS213, WPS231
    record_type: entities.AllowedRecordType,
    ip: Optional[str],
    cname: Optional[str],
    mail_host: Optional[str],
    name_server_host: Optional[str],
    text: Optional[str],
    protocol: Optional[str],
    service: Optional[str],
    weight: Optional[int],
    port: Optional[int],
    target: Optional[str],
    priority: Optional[int],
):
    getted_fields = {'name', 'type', 'ttl'}
    if ip is not None:
        getted_fields.add('ip')
    if cname is not None:
        getted_fields.add('canonical-name')
    if mail_host is not None:
        getted_fields.add('mail-host')
    if name_server_host is not None:
        getted_fields.add('name-server-host')
    if text is not None:
        getted_fields.add('text')
    if protocol is not None:
        getted_fields.add('protocol')
    if service is not None:
        getted_fields.add('service')
    if weight is not None:
        getted_fields.add('weight')
    if port is not None:
        getted_fields.add('port')
    if target is not None:
        getted_fields.add('target')
    if priority is not None:
        getted_fields.add('priority')

    record_entity_type = entities.get_record_entity_by_type(record_type)
    if not record_entity_type:
        raise WrongRecordType

    # convert inner field name to external value
    all_necessary_fields = {
        field.replace('_', '-') for field in record_entity_type.__annotations__  # noqa:WPS609
    }

    if set(all_necessary_fields) == getted_fields:
        return

    necessary_fields = all_necessary_fields - getted_fields
    extra_fields = getted_fields - all_necessary_fields
    raise WrongFieldSetGetted(
        record_type=record_type.value,
        necessary_fields=necessary_fields,
        extra_fields=extra_fields,
    )


class WrongRecordType(click.UsageError):
    def __init__(self) -> None:
        super().__init__('You can use only allowed dns record types')


class WrongFieldSetGetted(click.UsageError):
    def __init__(
        self,
        record_type: str,
        necessary_fields: Iterable[str],
        extra_fields: Iterable[str],
    ) -> None:
        msg = 'Wrong set of field for {record_type}.'.format(record_type=record_type)
        if necessary_fields:
            msg += ' Necessary fields {nec_field}'.format(nec_field=', '.join(necessary_fields))
        if extra_fields:
            msg += ' Extra fields {extra_fields}'.format(extra_fields=', '.join(extra_fields))
        super().__init__(msg)
