from unittest.mock import patch

from click.testing import CliRunner

from s2ctl.entrypoint import entry_point
from ssclient.http_client import HttpClient
from ssclient.metainfo import LocationEntity


def test_get_locations():
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
        result = runner.invoke(entry_point, ('-k', '02dadsd', 'locations', '--output=json'))
        make_request.assert_awaited()
        args = make_request.await_args[0]
        assert args[0] == 'GET'
        assert 'locations' in args[1]
        assert result.exit_code == 0
