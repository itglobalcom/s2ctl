"""Конфигурация и её keyring: сценарий README «стенд в отдельном файле, переданном через -c».

Обратной совместимости у этих правил нет: до задачи `--config` роняла CLI всегда.
"""
import random

import yaml
from click.testing import CliRunner

from s2ctl.config import KEYRING_FILE_NAME, ConfigManager, generate_password
from s2ctl.entrypoint import entry_point
from tests.s2ctl.conftest import APIKEY

_STAND_CONFIG = 'host: https://api.stand.example\n'
# Ключ, сгенерированный прошлым релизом: тот же алфавит, только источник случайности
# у него был `random`.
_KEY_OF_A_PREVIOUS_RELEASE = "'$]z2GZ&*.'"


def _stand_config(tmp_path):
    config_path = tmp_path / 'stands' / 'stand.yaml'
    config_path.parent.mkdir()
    config_path.write_text(_STAND_CONFIG)
    return config_path


def test_keyring_of_a_config_lives_next_to_it(tmp_path, cli_config):
    config_path = _stand_config(tmp_path)

    config = ConfigManager(config_path).get_config()

    # Ключ шифрования свой у каждого файла конфигурации, поэтому и keyring свой:
    # общий файл keyring второй конфигурации уже не расшифровать.
    assert config['keyring'] == str(config_path.parent / KEYRING_FILE_NAME)


def test_generated_keyring_key_is_kept_in_the_config(tmp_path, cli_config):
    config_path = _stand_config(tmp_path)
    config_manager = ConfigManager(config_path)

    first_key = config_manager.get_config()['keyring_key']
    second_key = config_manager.get_config()['keyring_key']

    # Ключ генерируется один раз и дописывается в файл: иначе следующий вызов
    # не откроет keyring, созданный предыдущим.
    assert first_key == second_key
    assert yaml.safe_load(config_path.read_text())['keyring_key'] == first_key


def test_keyring_locked_with_another_key_is_reported_without_traceback(tmp_path, cli_config):
    config_path = _stand_config(tmp_path)
    runner = CliRunner()
    assert runner.invoke(entry_point, ('-c', str(config_path), 'context', 'list')).exit_code == 0
    stored = yaml.safe_load(config_path.read_text())
    stored['keyring_key'] = 'another-key'
    config_path.write_text(yaml.dump(stored))

    result = runner.invoke(entry_point, ('-c', str(config_path), 'context', 'list'))

    assert result.exit_code != 0
    assert "Can't unlock the keyring" in result.output
    assert 'Traceback' not in result.output


def test_blank_keyring_key_is_named_as_the_thing_to_fix(tmp_path, cli_config):
    config_path = _stand_config(tmp_path)
    config_path.write_text(_STAND_CONFIG + "keyring_key: ''\n")

    result = CliRunner().invoke(
        entry_point, ('-c', str(config_path), '-k', 'apikey', 'context', 'list'),
    )

    assert result.exit_code != 0
    # Файла keyring на диске ещё нет — про «создан другим ключом» говорить нечего.
    assert 'The keyring key is empty' in result.output
    assert 'another key' not in result.output


def test_keyring_key_without_value_is_reported_without_traceback(tmp_path, cli_config):
    config_path = _stand_config(tmp_path)
    config_path.write_text(_STAND_CONFIG + 'keyring_key:\n')

    result = CliRunner().invoke(
        entry_point, ('-c', str(config_path), '-k', 'apikey', 'context', 'list'),
    )

    assert result.exit_code != 0
    assert 'The keyring key is empty' in result.output
    assert not isinstance(result.exception, AttributeError)


def test_keyring_file_of_another_scheme_is_named_as_alien(tmp_path, cli_config):
    config_path = _stand_config(tmp_path)
    runner = CliRunner()
    assert runner.invoke(entry_point, ('-c', str(config_path), 'context', 'list')).exit_code == 0
    keyring_path = tmp_path / 'stands' / KEYRING_FILE_NAME
    keyring_path.write_text(keyring_path.read_text().replace('AES128.GCM', 'AES256.CFB'))

    result = runner.invoke(entry_point, ('-c', str(config_path), 'context', 'list'))

    assert result.exit_code != 0
    assert 'another tool or another version' in result.output
    assert 'CFB' in result.output


def test_generated_keyring_key_is_not_reproducible_from_the_seeded_random():
    """Ключ шифрования keyring — секрет: `random` предсказуем по своему состоянию."""
    random.seed(0)
    first_key = generate_password()
    random.seed(0)
    second_key = generate_password()

    assert first_key != second_key


def test_keyring_key_stored_by_a_previous_release_still_opens_its_keyring(tmp_path, cli_config):
    """Ключ уже созданного конфига лежит в файле, и смена генератора его не касается."""
    config_path = _stand_config(tmp_path)
    config_path.write_text(_STAND_CONFIG + 'keyring_key: {key}\n'.format(key=_KEY_OF_A_PREVIOUS_RELEASE))
    runner = CliRunner()
    created = runner.invoke(
        entry_point, ('-c', str(config_path), 'context', 'create', '-n', 'stand', '-k', APIKEY),
    )
    assert created.exit_code == 0, created.output

    result = runner.invoke(entry_point, ('-c', str(config_path), 'context', 'show'))

    assert result.exit_code == 0, result.output
    assert 'stand' in result.output


def test_keyring_is_not_opened_by_a_command_that_does_not_need_it(tmp_path, cli_config, monkeypatch):
    """Хранилище открывается только там, где действительно читается.

    Открытие расшифровывает файл и стоит argon2 — доли секунды. Команда, которой
    ключ приходит из `--apikey`, и вывод справки не должны их платить.
    """
    config_path = _stand_config(tmp_path)
    opened = []
    monkeypatch.setattr(
        's2ctl.context.CryptFileKeyring',
        lambda *args, **kwargs: opened.append(1) or _fail_if_used(),
    )
    runner = CliRunner()

    assert runner.invoke(entry_point, ('-c', str(config_path), 'server', '--help')).exit_code == 0
    assert runner.invoke(entry_point, ('-c', str(config_path), 'context', '--help')).exit_code == 0

    assert not opened, 'keyring открыт там, где не нужен'


def _fail_if_used():
    raise AssertionError('keyring не должен создаваться для этих команд')
