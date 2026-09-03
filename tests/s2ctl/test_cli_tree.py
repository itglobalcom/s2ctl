from click.testing import CliRunner

from s2ctl.entrypoint import entry_point

# Состав CLI: группа или команда попадает сюда, только если её модуль импортирован
# в s2ctl/__init__.py — незарегистрированный модуль не виден ни в CLI, ни в бинаре
# (bundle/bundle.py импортирует один s2ctl.entrypoint).
EXPECTED_TOP_LEVEL_COMMANDS = frozenset({
    'affinity-group',
    'ansible',
    'applications',
    'context',
    'domain',
    'gateway',
    'images',
    'install-autocomplete',
    'locations',
    'network',
    'project',
    'server',
    'ssh-key',
    'task',
    'vmware',
})

EXPECTED_AFFINITY_GROUP_COMMANDS = frozenset({
    'create',
    'delete',
    'get',
    'list',
})

EXPECTED_GATEWAY_COMMANDS = frozenset({
    'add-nic',
    'add-tag',
    'create',
    'delete',
    'delete-nic',
    'delete-tag',
    'get',
    'get-firewall',
    'get-nat',
    'list',
    'rename',
    'replace-firewall',
    'replace-nat',
    'restart',
    'set-bandwidth',
    'start',
    'stop',
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
    'edit-nic',
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
    'price',
    'reboot',
    'rename',
    'rollback-snapshot',
    'set-configuration',
})


EXPECTED_VMWARE_COMMANDS = frozenset({
    'edge',
    'gpu-models',
    'images',
    'locations',
    'network',
    'server',
})

EXPECTED_VMWARE_NETWORK_COMMANDS = frozenset({
    'connect-servers',
    'create-isolated',
    'create-public',
    'create-routed',
    'delete',
    'get',
    'list',
    'rename',
    'set-bandwidth',
})

EXPECTED_VMWARE_SERVER_COMMANDS = frozenset({
    'copy',
    'create',
    'delete',
    'disable-nested-hypervisor',
    'enable-nested-hypervisor',
    'get',
    'get-firewall',
    'list',
    'power-off',
    'power-on',
    'reboot',
    'rebuild',
    'rename',
    'reset',
    'set-computer-name',
    'set-configuration',
    'shutdown',
    'update-firewall',
    'verify',
})

EXPECTED_VMWARE_EDGE_COMMANDS = frozenset({
    'delete-nat-rule',
    'delete-vpn-tunnel',
    'get-firewall',
    'get-nat',
    'get-vpn',
    'set-bandwidth',
    'update-firewall',
    'upsert-nat-rule',
    'upsert-vpn-tunnel',
})


def test_top_level_commands_registered():
    assert set(entry_point.commands) == EXPECTED_TOP_LEVEL_COMMANDS


def test_server_group_commands_registered():
    assert set(entry_point.commands['server'].commands) == EXPECTED_SERVER_COMMANDS


def test_gateway_group_commands_registered():
    assert set(entry_point.commands['gateway'].commands) == EXPECTED_GATEWAY_COMMANDS


def test_vmware_group_commands_registered():
    assert set(entry_point.commands['vmware'].commands) == EXPECTED_VMWARE_COMMANDS


def test_vmware_network_group_commands_registered():
    vmware_group = entry_point.commands['vmware']

    assert set(vmware_group.commands['network'].commands) == EXPECTED_VMWARE_NETWORK_COMMANDS


def test_vmware_server_group_commands_registered():
    vmware_group = entry_point.commands['vmware']

    assert set(vmware_group.commands['server'].commands) == EXPECTED_VMWARE_SERVER_COMMANDS


def test_vmware_edge_group_commands_registered():
    vmware_group = entry_point.commands['vmware']

    assert set(vmware_group.commands['edge'].commands) == EXPECTED_VMWARE_EDGE_COMMANDS


def test_affinity_group_commands_registered():
    assert set(entry_point.commands['affinity-group'].commands) == EXPECTED_AFFINITY_GROUP_COMMANDS


def test_help_lists_every_top_level_command():
    runner = CliRunner()

    result = runner.invoke(entry_point, ('--help',))

    assert result.exit_code == 0
    listed = set(result.output.split())
    assert EXPECTED_TOP_LEVEL_COMMANDS <= listed
