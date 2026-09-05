"""
Проверяемая таблица «операция Public API → команда CLI» — та же, что в README.

Знаменатель — снимок маршрутов контракта `contract_operations.txt` рядом:
он снят с исходников publisher'а `tools/dump_contract_operations.py`, и таблица
сверяется с ним, а не со списком, набранным здесь руками. Появившаяся у
publisher'а операция роняет прогон в тот момент, когда снимок поднимают на новую
ревизию, — и до появления команды объём задачи виден в diff'е снимка.
"""
import pathlib
import re
from typing import Dict, FrozenSet, Iterator, Tuple

import click

from s2ctl.entrypoint import entry_point

CONTRACT_SNAPSHOT = pathlib.Path(__file__).with_name('contract_operations.txt')

_REVISION_LINE = re.compile(r'^# publisher: cloudmng @ [0-9a-f]{40}$', re.MULTILINE)

# Соответствие не один-к-одному: одна команда закрывает несколько операций
# (`task get` — все форматы id задачи), и наоборот — `PUT vmware/networks/{id}`
# меняет и имя, и полосу, поэтому развёрнут в две команды.
COMMANDS_BY_OPERATION: Dict[str, Tuple[str, ...]] = {
    # 1.2 — задачи
    'GET /api/v1/tasks/{task_id}': ('task get',),
    'GET /api/v1/tasks/dns{task_id}': ('task get',),
    'GET /api/v1/tasks/vmw{task_id}': ('task get',),
    'GET /api/v1/tasks/already_completed_task': ('task get',),
    # 1.3 — affinity-группы, приложения, сервер
    'GET /api/v1/affinity-groups': ('affinity-group list',),
    'POST /api/v1/affinity-groups': ('affinity-group create',),
    'GET /api/v1/affinity-groups/{affinity_group_id}': ('affinity-group get',),
    'DELETE /api/v1/affinity-groups/{affinity_group_id}': ('affinity-group delete',),
    'GET /api/v1/applications': ('applications',),
    'POST /api/v1/servers/price': ('server price',),
    'PUT /api/v1/servers/{server_id}': ('server set-configuration',),
    'PUT /api/v1/servers/{server_id}/name': ('server rename',),
    'PUT /api/v1/servers/{server_id}/nics/{nic_id}': ('server edit-nic',),
    # 1.4 — шлюзы
    'GET /api/v1/gateways': ('gateway list',),
    'POST /api/v1/gateways': ('gateway create',),
    'GET /api/v1/gateways/l{location_id}e{gateway_id}': ('gateway get',),
    'PUT /api/v1/gateways/l{location_id}e{gateway_id}': ('gateway rename',),
    'DELETE /api/v1/gateways/l{location_id}e{gateway_id}': ('gateway delete',),
    'PUT /api/v1/gateways/l{location_id}e{gateway_id}/bandwidth': ('gateway set-bandwidth',),
    'GET /api/v1/gateways/l{location_id}e{gateway_id}/firewall': ('gateway get-firewall',),
    'PUT /api/v1/gateways/l{location_id}e{gateway_id}/firewall': ('gateway replace-firewall',),
    'GET /api/v1/gateways/l{location_id}e{gateway_id}/nat': ('gateway get-nat',),
    'PUT /api/v1/gateways/l{location_id}e{gateway_id}/nat': ('gateway replace-nat',),
    'POST /api/v1/gateways/l{location_id}e{gateway_id}/nics': ('gateway add-nic',),
    'DELETE /api/v1/gateways/l{location_id}e{gateway_id}/nics/{nic_id}': ('gateway delete-nic',),
    'POST /api/v1/gateways/l{location_id}e{gateway_id}/start': ('gateway start',),
    'POST /api/v1/gateways/l{location_id}e{gateway_id}/stop': ('gateway stop',),
    'POST /api/v1/gateways/l{location_id}e{gateway_id}/restart': ('gateway restart',),
    'POST /api/v1/gateways/l{location_id}e{gateway_id}/tags': ('gateway add-tag',),
    'DELETE /api/v1/gateways/l{location_id}e{gateway_id}/tags/{**tag}': ('gateway delete-tag',),
    # 1.5 — каталог VMware, сети и edge
    'GET /api/v1/vmware/locations': ('vmware locations',),
    'GET /api/v1/vmware/images': ('vmware images',),
    'GET /api/v1/vmware/gpu-models': ('vmware gpu-models',),
    'GET /api/v1/vmware/networks': ('vmware network list',),
    'POST /api/v1/vmware/networks/isolated': ('vmware network create-isolated',),
    'POST /api/v1/vmware/networks/public': ('vmware network create-public',),
    'POST /api/v1/vmware/networks/routed': ('vmware network create-routed',),
    'GET /api/v1/vmware/networks/{network_id}': ('vmware network get',),
    'PUT /api/v1/vmware/networks/{network_id}': ('vmware network rename', 'vmware network set-bandwidth'),
    'DELETE /api/v1/vmware/networks/{network_id}': ('vmware network delete',),
    'POST /api/v1/vmware/networks/{network_id}/servers': ('vmware network connect-servers',),
    'PUT /api/v1/vmware/networks/{network_id}/edge/bandwidth': ('vmware edge set-bandwidth',),
    'GET /api/v1/vmware/networks/{network_id}/edge/firewall': ('vmware edge get-firewall',),
    'PUT /api/v1/vmware/networks/{network_id}/edge/firewall': ('vmware edge replace-firewall',),
    'GET /api/v1/vmware/networks/{network_id}/edge/nat': ('vmware edge get-nat',),
    'POST /api/v1/vmware/networks/{network_id}/edge/nat': ('vmware edge upsert-nat-rule',),
    'DELETE /api/v1/vmware/networks/{network_id}/edge/nat/{rule_id}': ('vmware edge delete-nat-rule',),
    'GET /api/v1/vmware/networks/{network_id}/edge/vpn': ('vmware edge get-vpn',),
    'POST /api/v1/vmware/networks/{network_id}/edge/vpn': ('vmware edge upsert-vpn-tunnel',),
    'DELETE /api/v1/vmware/networks/{network_id}/edge/vpn/{tunnel_id}': ('vmware edge delete-vpn-tunnel',),
    # 1.6 — серверы VMware
    'GET /api/v1/vmware/servers': ('vmware server list',),
    'POST /api/v1/vmware/servers': ('vmware server create',),
    'POST /api/v1/vmware/servers/verify': ('vmware server verify',),
    'GET /api/v1/vmware/servers/{server_id}': ('vmware server get',),
    'PUT /api/v1/vmware/servers/{server_id}': ('vmware server set-configuration',),
    'DELETE /api/v1/vmware/servers/{server_id}': ('vmware server delete',),
    'PUT /api/v1/vmware/servers/{server_id}/name': ('vmware server rename',),
    'PUT /api/v1/vmware/servers/{server_id}/computer-name': ('vmware server set-computer-name',),
    'POST /api/v1/vmware/servers/{server_id}/copy': ('vmware server copy',),
    'POST /api/v1/vmware/servers/{server_id}/rebuild': ('vmware server rebuild',),
    'GET /api/v1/vmware/servers/{server_id}/firewall': ('vmware server get-firewall',),
    'PUT /api/v1/vmware/servers/{server_id}/firewall': ('vmware server replace-firewall',),
    'POST /api/v1/vmware/servers/{server_id}/nested-hypervisor/enable': ('vmware server enable-nested-hypervisor',),
    'POST /api/v1/vmware/servers/{server_id}/nested-hypervisor/disable': ('vmware server disable-nested-hypervisor',),
    'POST /api/v1/vmware/servers/{server_id}/power/on': ('vmware server power-on',),
    'POST /api/v1/vmware/servers/{server_id}/power/off': ('vmware server power-off',),
    'POST /api/v1/vmware/servers/{server_id}/power/shutdown': ('vmware server shutdown',),
    'POST /api/v1/vmware/servers/{server_id}/power/reboot': ('vmware server reboot',),
    'POST /api/v1/vmware/servers/{server_id}/power/reset': ('vmware server reset',),
    # 1.7 — диски, интерфейсы и снимок VMware-сервера
    'GET /api/v1/vmware/servers/{server_id}/volumes': ('vmware server list-volume',),
    'POST /api/v1/vmware/servers/{server_id}/volumes': ('vmware server add-volume',),
    'GET /api/v1/vmware/servers/{server_id}/volumes/{volume_id}': ('vmware server get-volume',),
    'PUT /api/v1/vmware/servers/{server_id}/volumes/{volume_id}': ('vmware server edit-volume',),
    'DELETE /api/v1/vmware/servers/{server_id}/volumes/{volume_id}': ('vmware server delete-volume',),
    'GET /api/v1/vmware/servers/{server_id}/nics': ('vmware server list-nic',),
    'POST /api/v1/vmware/servers/{server_id}/nics': ('vmware server connect-client-network',),
    'POST /api/v1/vmware/servers/{server_id}/nics/shared': ('vmware server connect-shared-network',),
    'PUT /api/v1/vmware/servers/{server_id}/nics/{nic_id}': ('vmware server edit-nic',),
    'DELETE /api/v1/vmware/servers/{server_id}/nics/{nic_id}': ('vmware server disconnect-nic',),
    'GET /api/v1/vmware/servers/{server_id}/snapshot': ('vmware server get-snapshot',),
    'POST /api/v1/vmware/servers/{server_id}/snapshot': ('vmware server create-snapshot',),
    'POST /api/v1/vmware/servers/{server_id}/snapshot/restore': ('vmware server restore-snapshot',),
    'DELETE /api/v1/vmware/servers/{server_id}/snapshot': ('vmware server delete-snapshot',),
    # покрыто до задачи — vStack-ядро, DNS, ssh-ключи, проект, каталог
    'GET /api/v1/locations': ('locations',),
    'GET /api/v1/images': ('images',),
    'GET /api/v1/project': ('project show',),
    'GET /api/v1/ssh-keys': ('ssh-key list',),
    'POST /api/v1/ssh-keys': ('ssh-key create',),
    'GET /api/v1/ssh-keys/{ssh_key_id}': ('ssh-key get',),
    'DELETE /api/v1/ssh-keys/{ssh_key_id}': ('ssh-key delete',),
    'GET /api/v1/domains': ('domain list',),
    'POST /api/v1/domains': ('domain create',),
    'GET /api/v1/domains/{domain_name}': ('domain get',),
    'DELETE /api/v1/domains/{domain_name}': ('domain delete',),
    'GET /api/v1/domains/{domain_name}/records': ('domain list-record',),
    'POST /api/v1/domains/{domain_name}/records': ('domain create-record',),
    'GET /api/v1/domains/{domain_name}/records/{record_id}': ('domain get-record',),
    'PUT /api/v1/domains/{domain_name}/records/{record_id}': ('domain update-record',),
    'DELETE /api/v1/domains/{domain_name}/records/{record_id}': ('domain delete-record',),
    'GET /api/v1/networks/isolated': ('network list',),
    'POST /api/v1/networks/isolated': ('network create',),
    'GET /api/v1/networks/isolated/{network_id}': ('network get',),
    'PUT /api/v1/networks/isolated/{network_id}': ('network edit',),
    'DELETE /api/v1/networks/isolated/{network_id}': ('network delete',),
    'POST /api/v1/networks/isolated/{network_id}/tags': ('network add-tag',),
    'DELETE /api/v1/networks/isolated/{network_id}/tags/{**tag}': ('network delete-tag',),
    'GET /api/v1/servers': ('server list',),
    'POST /api/v1/servers': ('server create',),
    'GET /api/v1/servers/{server_id}': ('server get',),
    'PATCH /api/v1/servers/{server_id}': ('server edit',),
    'DELETE /api/v1/servers/{server_id}': ('server delete',),
    'GET /api/v1/servers/{server_id}/nics': ('server list-nic',),
    'POST /api/v1/servers/{server_id}/nics': ('server add-nic',),
    'GET /api/v1/servers/{server_id}/nics/{nic_id}': ('server get-nic',),
    'DELETE /api/v1/servers/{server_id}/nics/{nic_id}': ('server delete-nic',),
    'POST /api/v1/servers/{server_id}/power/on': ('server power-on',),
    'POST /api/v1/servers/{server_id}/power/off': ('server power-off',),
    'POST /api/v1/servers/{server_id}/power/shutdown': ('server shutdown',),
    'POST /api/v1/servers/{server_id}/power/reboot': ('server reboot',),
    'POST /api/v1/servers/{server_id}/power/reset': ('server reset',),
    'GET /api/v1/servers/{server_id}/volumes': ('server list-volume',),
    'POST /api/v1/servers/{server_id}/volumes': ('server add-volume',),
    'GET /api/v1/servers/{server_id}/volumes/{volume_id}': ('server get-volume',),
    'PUT /api/v1/servers/{server_id}/volumes/{volume_id}': ('server edit-volume',),
    'DELETE /api/v1/servers/{server_id}/volumes/{volume_id}': ('server delete-volume',),
    'GET /api/v1/servers/{server_id}/snapshots': ('server list-snapshot',),
    'POST /api/v1/servers/{server_id}/snapshots': ('server create-snapshot',),
    'GET /api/v1/servers/{server_id}/snapshots/{snapshot_id}': ('server get-snapshot',),
    'DELETE /api/v1/servers/{server_id}/snapshots/{snapshot_id}': ('server delete-snapshot',),
    'POST /api/v1/servers/{server_id}/snapshots/{snapshot_id}/rollback': ('server rollback-snapshot',),
    'POST /api/v1/servers/{server_id}/tags': ('server add-tag',),
    'DELETE /api/v1/servers/{server_id}/tags/{**tag}': ('server delete-tag',),
}

# Раздел Kubernetes в CLI не поддерживается: его нет в опубликованном
# справочнике Public API, сервис feature-k8s в поддержке. «Частичной»
# поддержки быть не должно — отсюда тест на отсутствие команд раздела.
OPERATIONS_OUT_OF_SCOPE = frozenset({
    'DELETE /api/v1/k8s_clusters/{cluster_id}',
    'DELETE /api/v1/k8s_clusters/{cluster_id}/node_groups/{group_id}',
    'DELETE /api/v1/k8s_clusters/{cluster_id}/tags/{**tag}',
    'GET /api/v1/k8s_clusters',
    'GET /api/v1/k8s_clusters/{cluster_id}',
    'GET /api/v1/k8s_clusters/{cluster_id}/k8s_versions',
    'GET /api/v1/k8s_clusters/{cluster_id}/node_groups',
    'GET /api/v1/k8s_clusters/{cluster_id}/node_groups/{group_id}',
    'GET /api/v1/k8s_versions',
    'GET /api/v1/tasks/k8s_{task_id}',
    'POST /api/v1/k8s_clusters',
    'POST /api/v1/k8s_clusters/{cluster_id}/node_groups',
    'POST /api/v1/k8s_clusters/{cluster_id}/node_groups/{group_id}/ingress',
    'POST /api/v1/k8s_clusters/{cluster_id}/tags',
    'PUT /api/v1/k8s_clusters/{cluster_id}',
    'PUT /api/v1/k8s_clusters/{cluster_id}/node_groups/{group_id}',
})

# Команды, которые на операции контракта не мапятся: локальное состояние
# (контексты и ключи проектов в keyring), установка автодополнения и сборка
# ansible-инвентаря из уже прочитанных серверов.
NON_CONTRACT_COMMANDS = frozenset({
    'ansible get-inventory',
    'context create',
    'context delete',
    'context list',
    'context select',
    'context show',
    'install-autocomplete',
})

_KUBERNETES_MARKERS = ('k8s', 'kubernetes', 'cluster', 'node-group')


def _snapshot_operations() -> FrozenSet[str]:
    lines = CONTRACT_SNAPSHOT.read_text(encoding='utf-8').splitlines()
    return frozenset(
        line.strip()
        for line in lines
        if line.strip() and not line.startswith('#')
    )


def _command_leaves(command: click.Command, path: Tuple[str, ...] = ()) -> Iterator[str]:
    if isinstance(command, click.Group):
        for name, subcommand in command.commands.items():
            yield from _command_leaves(subcommand, path + (name,))
    else:
        yield ' '.join(path)


def _cli_commands() -> frozenset:
    return frozenset(_command_leaves(entry_point))


def _declared_commands() -> frozenset:
    return frozenset(
        command
        for commands in COMMANDS_BY_OPERATION.values()
        for command in commands
    )


def test_snapshot_names_the_revision_it_was_taken_from():
    # Снимок без ревизии publisher'а проверить не по чему: непонятно, чему он
    # был равен и что изменилось с тех пор.
    assert _REVISION_LINE.search(CONTRACT_SNAPSHOT.read_text(encoding='utf-8'))


def test_table_covers_the_whole_contract_surface():
    declared = set(COMMANDS_BY_OPERATION) | OPERATIONS_OUT_OF_SCOPE

    assert sorted(_snapshot_operations() - declared) == []
    assert sorted(declared - _snapshot_operations()) == []
    assert not set(COMMANDS_BY_OPERATION) & OPERATIONS_OUT_OF_SCOPE


def test_every_operation_in_scope_is_reachable_by_command():
    cli_commands = _cli_commands()

    unreachable = {
        operation: sorted(set(commands) - cli_commands)
        for operation, commands in COMMANDS_BY_OPERATION.items()
        if not set(commands) <= cli_commands
    }

    assert unreachable == {}


def test_every_command_is_declared_in_the_table():
    assert _cli_commands() == _declared_commands() | NON_CONTRACT_COMMANDS


def test_kubernetes_section_has_no_commands():
    kubernetes_commands = [
        command
        for command in _cli_commands()
        if any(marker in command for marker in _KUBERNETES_MARKERS)
    ]

    assert kubernetes_commands == []
