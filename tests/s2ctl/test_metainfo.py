from unittest.mock import patch

import pytest
from click.testing import CliRunner

from s2ctl.entrypoint import entry_point
from ssclient.http_client import HttpClient
from ssclient.metainfo import LocationEntity
from tests.s2ctl.conftest import APIKEY


def test_get_locations(cli_config):
    with patch.object(HttpClient, 'make_request') as make_request:
        id_ = 'test_id'
        make_request.return_value = {
            'locations': [LocationEntity(
                id='test_id',
                system_volume_min=1024,
                additional_volume_min=1024,
                volume_max=100,
                windows_system_volume_min=100,
                bandwidth_min=100,
                bandwidth_max=100,
                cpu_quantity_options=[1, 2],
                ram_size_options=[512, 1024],
            )],
        }
        runner = CliRunner()
        result = runner.invoke(entry_point, ('-k', APIKEY, 'locations', '--output=json'))
        make_request.assert_awaited()
        args = make_request.await_args[0]
        assert args[0] == 'GET'
        assert 'locations' in args[1]
        assert result.exit_code == 0


# Каталог приложений фильтруется тремя параметрами запроса, и у каждого своя опция:
# имена опций и имена параметров контракта расходятся (`--application` кладётся
# в `application_id`).
_APPLICATION_FILTERS = (
    (('--location', 'am2'), 'location_id=am2'),
    (('--application', 'docker'), 'application_id=docker'),
    (('--image', 'ubuntu-22-04'), 'image_id=ubuntu-22-04'),
)


@pytest.mark.parametrize('command_args,expected_query', _APPLICATION_FILTERS)
def test_applications_passes_its_filters_to_the_query_of_the_contract(
    cli_http_client, command_args, expected_query,
):
    expected_path = 'api/v1/applications?{query}'.format(query=expected_query)
    cli_http_client.on('GET', expected_path, {'applications': []})

    result = CliRunner().invoke(entry_point, ('-k', APIKEY, 'applications') + command_args)

    assert result.exit_code == 0, result.output
    assert cli_http_client.paths('GET') == [expected_path]
