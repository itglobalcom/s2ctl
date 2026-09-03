from click.testing import CliRunner

from s2ctl.entrypoint import entry_point
from ssclient.gateway.gateway_id import GATEWAY_ID_TEMPLATE
from ssclient.network.network_id import NETWORK_ID_TEMPLATE

_USAGE_ERROR_EXIT_CODE = 2


# cli_config — autouse, объявлена явно: без неё прогон пишет конфиг и keyring в домашний каталог.
def test_malformed_gateway_id_is_reported_as_bad_parameter(cli_config):
    runner = CliRunner()

    result = runner.invoke(entry_point, ('-k', '02dadsd', 'gateway', 'get', 'e1l2'))

    assert result.exit_code == _USAGE_ERROR_EXIT_CODE
    # Разбор id падает до запроса: пользователь видит формат id, а не traceback.
    assert GATEWAY_ID_TEMPLATE in result.output
    assert result.exc_info[0] is SystemExit


def test_malformed_network_id_of_new_nic_is_reported_as_bad_parameter(cli_config):
    runner = CliRunner()

    result = runner.invoke(
        entry_point, ('-k', '02dadsd', 'gateway', 'add-nic', 'l1e2', '--network-id', 'n1l3'),
    )

    assert result.exit_code == _USAGE_ERROR_EXIT_CODE
    assert NETWORK_ID_TEMPLATE in result.output
    assert result.exc_info[0] is SystemExit
