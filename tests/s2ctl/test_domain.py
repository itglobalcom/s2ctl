"""Связка «опция CLI → поле запроса контракта» для доменов и записей DNS."""
import pytest
from click.testing import CliRunner

from s2ctl.entrypoint import entry_point
from tests.conftest import FakeRequest
from tests.s2ctl.conftest import APIKEY

DOMAIN_NAME = 'example.com'
RECORD_ID = 17

RECORDS_PATH = 'api/v1/domains/{domain}/records/'.format(domain=DOMAIN_NAME)
RECORD_PATH = '{path}{record_id}'.format(path=RECORDS_PATH, record_id=RECORD_ID)

_RECORD_ARGS = (
    'update-record', DOMAIN_NAME,
    '--record-id', str(RECORD_ID),
    '--name', 'www',
    '--ttl', '1h',
)

# Приоритет записи MX и вес с портом записи SRV publisher требует непустыми
# (`[EncodedRequired]` у `RecordMxCommand.Priority`, `RecordSrvCommand.Weight`
# и `.Port`), а нуль в них — штатное значение: наивысший приоритет обменника
# и «вес не участвует в выборе». Выпав из тела, такое значение даёт 400.
_ZERO_VALUED_RECORDS = (
    (
        ('--type', 'mx', '--mail-host', 'mx.example.com', '--priority', '0'),
        {'mail_host': 'mx.example.com', 'priority': 0},
    ),
    (
        (
            '--type', 'srv',
            '--protocol', 'tcp',
            '--service', 'sip',
            '--target', 'sip.example.com.',
            '--priority', '0',
            '--weight', '0',
            '--port', '0',
        ),
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


def _invoke(*args):
    return CliRunner().invoke(entry_point, ('-k', APIKEY, 'domain') + args)


@pytest.mark.parametrize('record_args,expected_fields', _ZERO_VALUED_RECORDS)
def test_zero_valued_option_of_a_record_reaches_the_request(
    cli_http_client, record_args, expected_fields,
):
    cli_http_client.on('PUT', RECORD_PATH, {'task_id': 'dns9'})

    result = _invoke(*_RECORD_ARGS, *record_args)

    assert result.exit_code == 0, result.output
    assert cli_http_client.requests == [FakeRequest('PUT', RECORD_PATH, {
        'name': 'www',
        'type': record_args[1],
        'ttl': '1h',
        **expected_fields,
    })]


# Удаления DNS тоже спрашивают ссылку на задачу: `DnsControllerBase.DeleteOk`
# отдаёт её по тому же `return_task=true`, только id приходит в форме `dns{id}`.
_DELETE_COMMANDS = (
    (('delete', DOMAIN_NAME), 'api/v1/domains/{domain}'.format(domain=DOMAIN_NAME)),
    (('delete-record', DOMAIN_NAME, '--record-id', str(RECORD_ID)), RECORD_PATH),
)


@pytest.mark.parametrize('command_args,path', _DELETE_COMMANDS)
def test_delete_asks_the_publisher_for_the_reference_to_the_task(
    cli_http_client, command_args, path,
):
    expected_path = '{path}?return_task=true'.format(path=path)
    cli_http_client.on('DELETE', expected_path, {'task_id': 'dns9'})

    result = _invoke(*command_args)

    assert result.exit_code == 0, result.output
    assert cli_http_client.paths('DELETE') == [expected_path]
    assert 'dns9' in result.output
