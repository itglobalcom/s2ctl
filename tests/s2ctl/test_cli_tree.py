from click.testing import CliRunner

from s2ctl.entrypoint import entry_point

# Состав CLI: группа или команда попадает сюда, только если её модуль импортирован
# в s2ctl/__init__.py — незарегистрированный модуль не виден ни в CLI, ни в бинаре
# (bundle/bundle.py импортирует один s2ctl.entrypoint).
EXPECTED_TOP_LEVEL_COMMANDS = frozenset({
    'ansible',
    'context',
    'domain',
    'images',
    'install-autocomplete',
    'locations',
    'network',
    'project',
    'server',
    'ssh-key',
    'task',
})

EXPECTED_SERVER_COMMANDS = frozenset({
    'add-nic',
    'add-tag',
    'add-volume',
    'create',
    'create-snapshot',
    'delete',
    'delete-nic',
    'delete-snapshot',
    'delete-tag',
    'delete-volume',
    'edit',
    'edit-volume',
    'get',
    'get-nic',
    'get-volume',
    'list',
    'list-nic',
    'list-snapshot',
    'list-volume',
    'power-off',
    'power-on',
    'reboot',
    'rollback-snapshot',
})


def test_top_level_commands_registered():
    assert set(entry_point.commands) == EXPECTED_TOP_LEVEL_COMMANDS


def test_server_group_commands_registered():
    assert set(entry_point.commands['server'].commands) == EXPECTED_SERVER_COMMANDS


def test_help_lists_every_top_level_command():
    runner = CliRunner()

    result = runner.invoke(entry_point, ('--help',))

    assert result.exit_code == 0
    listed = set(result.output.split())
    assert EXPECTED_TOP_LEVEL_COMMANDS <= listed
