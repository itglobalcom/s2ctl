from click.testing import CliRunner

from s2ctl.entrypoint import entry_point
from ssclient.affinity_group import AFFINITY_GROUP_ID_TEMPLATE

_USAGE_ERROR_EXIT_CODE = 2


# cli_config — autouse, объявлена явно: без неё прогон пишет конфиг и keyring в домашний каталог.
def test_malformed_group_id_is_reported_as_bad_parameter(cli_config):
    runner = CliRunner()

    result = runner.invoke(entry_point, ('-k', '02dadsd', 'affinity-group', 'get', 'g1l2'))

    assert result.exit_code == _USAGE_ERROR_EXIT_CODE
    # Разбор id падает до запроса: пользователь видит формат id, а не traceback.
    assert AFFINITY_GROUP_ID_TEMPLATE in result.output
    assert result.exc_info[0] is SystemExit
