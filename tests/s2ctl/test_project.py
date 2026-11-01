import json

import pytest
from click.testing import CliRunner

from s2ctl.entrypoint import entry_point
from tests.s2ctl.conftest import APIKEY

_ENVELOPE = {
    'from': '2026-10-01',
    'to': '2026-10-31',
    'time_zone': 'Europe/Moscow',
    'currency': 'RUB',
    'is_final': True,
    'total': 100.5,
}

_COMMAND_CASES = (
    ('consumption', 'api/v1/project/consumption', 'services'),
    ('consumption-resources', 'api/v1/project/consumption/resources', 'resources'),
    ('consumption-daily', 'api/v1/project/consumption/daily', 'days'),
)


@pytest.mark.parametrize('command,path,breakdown', _COMMAND_CASES)
def test_consumption_prints_the_envelope_of_the_contract_whole(
    cli_http_client, command, path, breakdown,
):
    envelope = {**_ENVELOPE, breakdown: []}
    cli_http_client.on('GET', path, {'consumption': envelope})

    result = CliRunner().invoke(entry_point, ('-k', APIKEY, 'project', command, '--output=json'))

    assert result.exit_code == 0, result.output
    assert cli_http_client.paths('GET') == [path]
    assert json.loads(result.output) == envelope


@pytest.mark.parametrize('command,path,breakdown', _COMMAND_CASES)
def test_consumption_passes_its_period_to_the_query_of_the_contract(
    cli_http_client, command, path, breakdown,
):
    expected_path = '{path}?from=2026-10-01&to=2026-10-31'.format(path=path)
    cli_http_client.on('GET', expected_path, {'consumption': {**_ENVELOPE, breakdown: []}})

    result = CliRunner().invoke(entry_point, (
        '-k', APIKEY, 'project', command, '--from', '2026-10-01', '--to', '2026-10-31',
    ))

    assert result.exit_code == 0, result.output
    assert cli_http_client.paths('GET') == [expected_path]


def test_consumption_resources_passes_its_service_to_the_query_of_the_contract(cli_http_client):
    expected_path = 'api/v1/project/consumption/resources?service=cloud_director'
    cli_http_client.on('GET', expected_path, {'consumption': {**_ENVELOPE, 'resources': []}})

    result = CliRunner().invoke(entry_point, (
        '-k', APIKEY, 'project', 'consumption-resources', '--service', 'cloud_director',
    ))

    assert result.exit_code == 0, result.output
    assert cli_http_client.paths('GET') == [expected_path]


@pytest.mark.parametrize('command,path,breakdown', _COMMAND_CASES)
def test_consumption_refuses_a_date_out_of_format_before_the_request(
    cli_http_client, command, path, breakdown,
):
    result = CliRunner().invoke(entry_point, (
        '-k', APIKEY, 'project', command, '--from', '01.10.2026',
    ))

    assert result.exit_code == 2
    assert '--from' in result.output
    assert cli_http_client.requests == []
