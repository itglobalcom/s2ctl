"""Домены и записи DNS: `--wait` адресует созданный ресурс через `resources[]` задачи.

Регресс на миграцию с legacy-полей задачи (`domain_id`, `record_id`) на `resources[]`:
ошибка в типе ресурса вылезала бы только в рантайме, на живой задаче.
"""
import pytest

from ssclient.domain.domain import DomainService
from ssclient.domain.record import RecordService
from ssclient.domain.record_entities import AllowedRecordType, AllowedTTLType
from ssclient.task_entities import TaskState
from tests.conftest import task_response

DOMAINS_PATH = 'api/v1/domains/'
DOMAIN_PATH = '{path}example.com'.format(path=DOMAINS_PATH)
RECORDS_PATH = '{domain_path}/records/'.format(domain_path=DOMAIN_PATH)
RECORD_PATH = '{path}17'.format(path=RECORDS_PATH)

DOMAIN_ENTITY = {'name': 'example.com', 'is_delegated': True, 'records': []}
RECORD_ENTITY = {'id': 17, 'name': 'www', 'type': 'A', 'ttl': '1h', 'ip': '10.0.0.5'}


async def test_create_domain_with_wait_reads_domain_from_task_resources(fake_http_client):
    fake_http_client.on('POST', DOMAINS_PATH, {'task_id': 'dns345'})
    fake_http_client.on(
        'GET', 'api/v1/tasks/dns345',
        task_response('dns345', TaskState.completed, resources=[
            ('record', '17'), ('domain', 'example.com'),
        ]),
    )
    fake_http_client.on('GET', DOMAIN_PATH, {'domain': DOMAIN_ENTITY})

    domain = await DomainService(fake_http_client).create(name='example.com', wait=True)

    # Домен берётся по типу ресурса, а не по первой записи `resources[]`.
    assert fake_http_client.paths('GET') == ['api/v1/tasks/dns345', DOMAIN_PATH]
    assert domain == DOMAIN_ENTITY


async def test_create_record_with_wait_reads_record_from_task_resources(fake_http_client):
    fake_http_client.on('POST', RECORDS_PATH, {'task_id': 'dns346'})
    fake_http_client.on(
        'GET', 'api/v1/tasks/dns346',
        task_response('dns346', TaskState.completed, resources=[
            ('domain', 'example.com'), ('record', '17'),
        ]),
    )
    fake_http_client.on('GET', RECORD_PATH, {'record': RECORD_ENTITY})

    record = await RecordService(fake_http_client, 'example.com').create_a(
        name='www', ttl=AllowedTTLType.one_h, ip='10.0.0.5', wait=True,
    )

    assert fake_http_client.paths('GET') == ['api/v1/tasks/dns346', RECORD_PATH]
    assert record == RECORD_ENTITY


async def test_update_record_with_wait_reads_record_from_task_resources(fake_http_client):
    fake_http_client.on('PUT', RECORD_PATH, {'task_id': 'dns347'})
    fake_http_client.on(
        'GET', 'api/v1/tasks/dns347',
        task_response('dns347', TaskState.completed, resources=[
            ('domain', 'example.com'), ('record', '17'),
        ]),
    )
    fake_http_client.on('GET', RECORD_PATH, {'record': RECORD_ENTITY})

    record = await RecordService(fake_http_client, 'example.com').update(
        17,
        name='www',
        ttl=AllowedTTLType.one_h,
        record_type=AllowedRecordType.a,
        ip='10.0.0.5',
        wait=True,
    )

    assert fake_http_client.paths('GET') == ['api/v1/tasks/dns347', RECORD_PATH]
    assert record == RECORD_ENTITY


# Нулевой приоритет записи MX и нулевые вес и порт записи SRV — штатные значения
# контракта, а не «поле не задано»: publisher требует их непустыми
# (`[EncodedRequired]` у `RecordMxCommand.Priority`, `RecordSrvCommand.Weight`
# и `.Port`) и на отсутствующем поле отвечает 400.
_ZERO_VALUED_UPDATES = (
    (
        {'record_type': AllowedRecordType.mx, 'mail_host': 'mx.example.com', 'priority': 0},
        {'mail_host': 'mx.example.com', 'priority': 0},
    ),
    (
        {
            'record_type': AllowedRecordType.srv,
            'protocol': 'tcp',
            'service': 'sip',
            'target': 'sip.example.com.',
            'priority': 0,
            'weight': 0,
            'port': 0,
        },
        {
            'protocol': 'tcp',
            'service': 'sip',
            'target': 'sip.example.com.',
            'priority': 0,
            'weight': 0,
            'port': 0,
        },
    ),
)


@pytest.mark.parametrize('update_fields,expected_fields', _ZERO_VALUED_UPDATES)
async def test_update_record_keeps_zero_values_in_the_request(
    fake_http_client, update_fields, expected_fields,
):
    fake_http_client.on('PUT', RECORD_PATH, {'task_id': 'dns348'})

    await RecordService(fake_http_client, 'example.com').update(
        17, name='www', ttl=AllowedTTLType.one_h, **update_fields,
    )

    assert fake_http_client.requests[0].payload == {
        'name': 'www',
        'type': update_fields['record_type'].value,
        'ttl': '1h',
        **expected_fields,
    }


async def test_update_record_omits_the_fields_of_other_record_types(fake_http_client):
    fake_http_client.on('PUT', RECORD_PATH, {'task_id': 'dns349'})

    await RecordService(fake_http_client, 'example.com').update(
        17,
        name='www',
        ttl=AllowedTTLType.one_h,
        record_type=AllowedRecordType.a,
        ip='10.0.0.5',
    )

    # Поле чужого типа записи publisher не принимает вовсе: в теле только свои.
    assert fake_http_client.requests[0].payload == {
        'name': 'www',
        'type': 'a',
        'ttl': '1h',
        'ip': '10.0.0.5',
    }


# У DNS своя база контроллеров, но `return_task=true` она понимает так же, как
# vStack: без параметра ответ удаления пуст, с ним — id задачи в форме `dns{id}`.
async def test_delete_domain_asks_the_publisher_for_the_reference_to_the_task(fake_http_client):
    expected_path = '{path}?return_task=true'.format(path=DOMAIN_PATH)
    fake_http_client.on('DELETE', expected_path, {'task_id': 'dns350'})
    fake_http_client.on('GET', 'api/v1/tasks/dns350', task_response('dns350', TaskState.completed))

    task_wrap = await DomainService(fake_http_client).delete('example.com', wait=True)

    assert fake_http_client.paths('DELETE') == [expected_path]
    assert fake_http_client.paths('GET') == ['api/v1/tasks/dns350']
    assert task_wrap is None


async def test_delete_record_asks_the_publisher_for_the_reference_to_the_task(fake_http_client):
    expected_path = '{path}?return_task=true'.format(path=RECORD_PATH)
    fake_http_client.on('DELETE', expected_path, {'task_id': 'dns351'})

    task_wrap = await RecordService(fake_http_client, 'example.com').delete(17)

    assert fake_http_client.paths('DELETE') == [expected_path]
    assert task_wrap == {'task_id': 'dns351'}
