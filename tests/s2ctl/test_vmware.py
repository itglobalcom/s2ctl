from click.testing import CliRunner

from s2ctl.entrypoint import entry_point

_USAGE_ERROR_EXIT_CODE = 2


# cli_config — autouse, объявлена явно: без неё прогон пишет конфиг и keyring в домашний каталог.
def test_public_network_capacity_is_enum_token_not_prefix_length(cli_config):
    runner = CliRunner()

    result = runner.invoke(entry_point, (
        '-k', '02dadsd',
        'vmware', 'network', 'create-public',
        '--location', '1', '--name', 'net', '--capacity', '26',
    ))

    # Размер блока публичных адресов publisher принимает именем члена enum
    # (`Network26`), а не числом: справочник Go SDK описывает это поле неверно.
    assert result.exit_code == _USAGE_ERROR_EXIT_CODE
    assert 'network26' in result.output.lower()


def test_malformed_server_nic_is_reported_as_bad_parameter(cli_config):
    runner = CliRunner()

    result = runner.invoke(entry_point, (
        '-k', '02dadsd',
        'vmware', 'network', 'connect-servers', '42', '--server', 'srv-1',
    ))

    # Разбор пары «сервер:адрес» падает до запроса: пользователь видит формат, а не traceback.
    assert result.exit_code == _USAGE_ERROR_EXIT_CODE
    assert 'SERVER_ID' in result.output
