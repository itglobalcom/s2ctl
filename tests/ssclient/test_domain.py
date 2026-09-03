"""Домены и записи DNS: `--wait` адресует созданный ресурс через `resources[]` задачи.

Регресс на миграцию с legacy-полей задачи (`domain_id`, `record_id`) на `resources[]`:
ошибка в типе ресурса вылезала бы только в рантайме, на живой задаче.
"""
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
