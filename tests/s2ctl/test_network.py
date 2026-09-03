from click.testing import CliRunner

from s2ctl.entrypoint import entry_point
from ssclient.network.network_id import NETWORK_ID_TEMPLATE

_USAGE_ERROR_EXIT_CODE = 2


# cli_config — autouse, объявлена явно: без неё прогон пишет конфиг и keyring в домашний каталог.
def test_malformed_network_id_is_reported_as_bad_parameter(cli_config):
    runner = CliRunner()

    result = runner.invoke(entry_point, ('-k', '02dadsd', 'network', 'get', 'n1l3'))

    assert result.exit_code == _USAGE_ERROR_EXIT_CODE
    # После перехода раздела на доменный тип мусорный id отсекается до запроса.
    assert NETWORK_ID_TEMPLATE in result.output
    assert result.exc_info[0] is SystemExit
