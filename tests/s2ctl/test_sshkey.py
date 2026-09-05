"""Связка «опция CLI → поле запроса контракта» для ssh-ключей проекта."""
from click.testing import CliRunner

from s2ctl.entrypoint import entry_point
from tests.conftest import FakeRequest
from tests.s2ctl.conftest import APIKEY

SSHKEYS_PATH = 'api/v1/ssh-keys'

_USAGE_ERROR_EXIT_CODE = 2

PUBLIC_KEY = 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5 user@host'

_KEY_ENTITY = {'id': 7, 'name': 'work', 'public_key': PUBLIC_KEY}


def _invoke(*args):
    return CliRunner().invoke(entry_point, ('-k', APIKEY, 'ssh-key') + args)


def test_key_given_by_option_is_sent_as_is(cli_http_client):
    cli_http_client.on('POST', SSHKEYS_PATH, _KEY_ENTITY)

    result = _invoke('create', '--name', 'work', '--public-key', PUBLIC_KEY)

    assert result.exit_code == 0, result.output
    assert cli_http_client.requests == [
        FakeRequest('POST', SSHKEYS_PATH, {'name': 'work', 'public_key': PUBLIC_KEY}),
    ]


def test_key_given_by_file_is_read_by_the_command(cli_http_client, tmp_path):
    key_file = tmp_path / 'id_ed25519.pub'
    key_file.write_text(PUBLIC_KEY)
    cli_http_client.on('POST', SSHKEYS_PATH, _KEY_ENTITY)

    result = _invoke('create', '--name', 'work', '--file', str(key_file))

    assert result.exit_code == 0, result.output
    assert cli_http_client.requests == [
        FakeRequest('POST', SSHKEYS_PATH, {'name': 'work', 'public_key': PUBLIC_KEY}),
    ]


def test_both_sources_of_the_key_are_refused(cli_http_client, tmp_path):
    key_file = tmp_path / 'id_ed25519.pub'
    key_file.write_text(PUBLIC_KEY)

    result = _invoke(
        'create', '--name', 'work', '--public-key', PUBLIC_KEY, '--file', str(key_file),
    )

    # Ключ приходит из одного источника: два заданных — противоречие во входе,
    # и запрос до publisher'а не доходит.
    assert result.exit_code == _USAGE_ERROR_EXIT_CODE
    assert cli_http_client.requests == []
    assert "can't be set at the same time" in result.output


def test_key_without_a_source_is_refused(cli_http_client):
    result = _invoke('create', '--name', 'work')

    assert result.exit_code == _USAGE_ERROR_EXIT_CODE
    assert cli_http_client.requests == []
    assert '--public-key' in result.output


def test_empty_key_file_is_refused(cli_http_client, tmp_path):
    key_file = tmp_path / 'empty.pub'
    key_file.write_text('')

    result = _invoke('create', '--name', 'work', '--file', str(key_file))

    # Пустой файл ключа — не ключ: раньше команда отправляла publisher'у пустую строку.
    assert result.exit_code == _USAGE_ERROR_EXIT_CODE
    assert cli_http_client.requests == []
    assert '--public-key' in result.output
