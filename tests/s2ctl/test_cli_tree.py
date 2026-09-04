import json
import sys
import types
from itertools import chain

import click
import pytest
from click.testing import CliRunner

from s2ctl import entrypoint, params
from s2ctl.entrypoint import entry_point
from ssclient.client import SSClient
from tests.s2ctl.conftest import APIKEY

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
    'get-snapshot',
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
    'reset',
    'rollback-snapshot',
    'set-configuration',
    'shutdown',
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
    'add-volume',
    'connect-client-network',
    'connect-shared-network',
    'copy',
    'create',
    'create-snapshot',
    'delete',
    'delete-snapshot',
    'delete-volume',
    'disable-nested-hypervisor',
    'disconnect-nic',
    'edit-nic',
    'edit-volume',
    'enable-nested-hypervisor',
    'get',
    'get-firewall',
    'get-snapshot',
    'get-volume',
    'list',
    'list-nic',
    'list-volume',
    'power-off',
    'power-on',
    'reboot',
    'rebuild',
    'rename',
    'replace-firewall',
    'reset',
    'restore-snapshot',
    'set-computer-name',
    'set-configuration',
    'shutdown',
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


# Инварианты состава команд проверяются обходом дерева, а не перечислением: команда,
# заведённая мимо общих декораторов `output_option`/`wait_option`, обязана падать здесь,
# а не обнаруживаться на ревью.

# Ссылка на задачу в ответе publisher'а: у заказа сервера рядом с ней едет id созданной
# машины, у подключения серверов к сети — по задаче на каждый сервер.
_TASK_REFERENCE_FIELDS = frozenset(('task_id', 'task_ids', 'server_id'))

# Значения обязательных параметров, которые заглушке всё равно, но команде — нет:
# составной id разбирается колбэком до запроса.
_ID_BY_PARSER = types.MappingProxyType({
    params.parse_gateway_id: 'l1e2',
    params.parse_network_id: 'l1n2',
    params.parse_network_ids: 'l1n2',
    params.parse_affinity_group_id: 'l1g2',
    params.parse_server_id: 'l1s2',
    params.parse_task_id: 'l2t3',
})

# Значения, которые команда иначе возьмёт не из аргументов: запись DNS требует поля
# своего типа, а установка автодополнения — оболочку из окружения прогона.
_EXTRA_ARGS = types.MappingProxyType({
    'domain create-record': ('--ip', '10.0.0.1'),
    'domain update-record': ('--ip', '10.0.0.1'),
    'install-autocomplete': ('bash',),
})

# Команды, про которые заглушка ничего сказать не может, и почему:
# ответ этих операций — тело самой сущности, а заглушка отвечает ссылкой на задачу
# на любой маршрут, поэтому ссылку от сущности здесь не отличить;
# `ansible get-inventory` операции контракта не соответствует вовсе — он собирает
# инвентарь из уже прочитанных серверов, и собирать его заглушке не из чего.
_STUB_BLIND_COMMANDS = frozenset({
    'ansible get-inventory',
    'gateway add-tag',
    'network add-tag',
    'network edit',
    'server add-tag',
    'server price',
    'ssh-key create',
})


class _AnyResponse(dict):
    """Ответ на любой маршрут: ссылка на задачу, а на любое поле — сущность под этим именем.

    Множественное имя поля даёт список сущностей, единственное — одну: этого хватает,
    чтобы довести до конца и команду чтения, и команду асинхронной операции.
    """

    def __missing__(self, key):
        entity = _AnyResponse({'id': key, 'name': key})
        if key.endswith('s'):
            return [entity]
        return entity


class _AnyApi(object):
    """Порт HTTP, отвечающий на любой запрос: маршруты проверены на клиентском слое."""

    async def get(self, path):
        return _AnyResponse({'task_id': 'l1t9'})

    async def post(self, path, payload=None):
        return _AnyResponse({'task_id': 'l1t9'})

    async def put(self, path, payload=None):
        return _AnyResponse({'task_id': 'l1t9'})

    async def patch(self, path, payload=None):
        return _AnyResponse({'task_id': 'l1t9'})

    async def delete(self, path):
        return _AnyResponse({'task_id': 'l1t9'})


def _commands_of_cli(command=entry_point, path=()):
    """Каждая команда и подгруппа CLI: сам `entry_point` — это CLI, а не команда в нём."""
    if isinstance(command, click.Group):
        for name, subcommand in command.commands.items():
            yield ' '.join(path + (name,)), subcommand
            yield from _commands_of_cli(subcommand, path + (name,))


def _leaf_commands(command=entry_point, path=()):
    if isinstance(command, click.Group):
        for name, subcommand in command.commands.items():
            yield from _leaf_commands(subcommand, path + (name,))
    else:
        yield ' '.join(path), command


def _argument_value(param, rules_path: str) -> str:
    if param.callback in _ID_BY_PARSER:
        return _ID_BY_PARSER[param.callback]
    if isinstance(param.type, click.Choice):
        return param.type.choices[0]
    if isinstance(param.type, click.File):
        return rules_path
    return '1'


def _required_args(command, rules_path: str):
    options, arguments = [], []
    for param in command.params:
        if not param.required:
            continue
        if isinstance(param, click.Argument):
            arguments.append(_argument_value(param, rules_path))
        elif getattr(param, 'is_bool_flag', False) or param.is_flag:
            options.append(param.opts[0])
        else:
            options.extend([param.opts[0], _argument_value(param, rules_path)])
    return tuple(options + arguments)


def _prints_task_reference(output: str) -> bool:
    try:
        printed = json.loads(output)
    except ValueError:
        return False
    if not isinstance(printed, dict):
        return False
    return bool(printed) and set(printed) <= _TASK_REFERENCE_FIELDS


class _EmptyContextManager(object):
    """Контексты без keyring: ключа проекта достать нечем, и открывать файл нечего.

    Открытие настоящего keyring — argon2 на каждый вызов CLI, и обход всего дерева
    команд с ним идёт минуты. Ключа в конфигурации прогона всё равно нет, поэтому
    подмена ничего не скрывает: команда, которой ключ нужен, отказывает и здесь.
    """

    def __init__(self, config_manager, keyring_key: str, keyring_path: str) -> None:
        self.config_manager = config_manager

    def get_current_apikey(self) -> None:
        raise RuntimeError("context doesn't exist")


@pytest.fixture
def without_api_key(cli_config, monkeypatch):
    monkeypatch.setattr(entrypoint, 'ContextManager', _EmptyContextManager)


@pytest.fixture
def stub_api(cli_config, monkeypatch, tmp_path):
    """Сервис команда берёт фабрикой клиента — подменяется она во всех модулях команд."""
    for module_name, module in tuple(sys.modules.items()):
        if module_name.startswith('s2ctl.cmd_') and hasattr(module, 'client_factory'):
            monkeypatch.setattr(module, 'client_factory', lambda _ctx: SSClient(_AnyApi()))

    # Ключ IPsec команда спрашивает интерактивно, если он не пришёл переменной окружения.
    monkeypatch.setenv('S2CTL_VPN_SHARED_KEY', 'secret')

    rules_path = tmp_path / 'rules.json'
    rules_path.write_text('[]')
    return str(rules_path)


def test_every_command_prints_through_the_shared_output_option():
    without_output = [
        name
        for name, command in _leaf_commands()
        if 'output' not in {param.name for param in command.params}
    ]

    # Печатать в машинном формате умеет любая команда: разбирать вывод CLI приходится
    # и скриптам пользователя, и следующей команде в конвейере.
    assert without_output == []


def test_help_of_every_command_needs_no_api_key(without_api_key):
    """Справка доступна без ключа проекта — на любой глубине дерева команд.

    Ключ нужен в момент вызова команды, а не разбора её группы: клиент API,
    созданный колбэком группы, делал бы `--help` подкоманды недоступным, потому
    что click выполняет группу до того, как доберётся до самого `--help`.
    """
    refused = {}
    for name, _command in _commands_of_cli():
        invocation = CliRunner().invoke(entry_point, tuple(name.split()) + ('--help',))
        if invocation.exit_code != 0:
            refused[name] = invocation.output

    assert refused == {}


def test_every_command_offers_a_description():
    without_description = [name for name, command in _commands_of_cli() if not command.help]

    # Описание команды — то, что видно в списке команд группы: без него `--help` группы
    # перечисляет имена, по которым выбрать команду можно только угадав.
    assert without_description == []


def test_every_option_offers_help():
    # Обход дерева команд начинается с самого `entry_point`: его глобальные опции
    # ни в одну команду не входят, а в справке печатаются наравне с ними.
    without_help = [
        '{name} {option}'.format(name=name, option=param.opts[0])
        for name, command in chain((('s2ctl', entry_point),), _commands_of_cli())
        for param in command.params
        if isinstance(param, click.Option) and not param.hidden and not param.help
    ]

    # Текст подсказки не проверяется — проверяется, что он есть: опция без help
    # печатается в справке одним своим именем, и назначение её пользователь узнаёт
    # только из отказа команды. Скрытая опция в справке не печатается вовсе.
    assert without_help == []


def test_asynchronous_command_is_exactly_the_one_that_offers_wait(stub_api):
    mismatched = {}
    for name, command in _leaf_commands():
        if name in _STUB_BLIND_COMMANDS:
            continue
        argv = tuple(name.split()) + _required_args(command, stub_api)
        argv += _EXTRA_ARGS.get(name, ()) + ('--output', 'json')
        invocation = CliRunner().invoke(entry_point, ('-k', APIKEY) + argv)

        assert invocation.exit_code == 0, '{name}: {output}'.format(
            name=name, output=invocation.output,
        )
        offers_wait = 'wait' in {param.name for param in command.params}
        if _prints_task_reference(invocation.output) != offers_wait:
            mismatched[name] = offers_wait

    # Ссылку на задачу команда отдаёт без `--wait` — это критерий приёмки: id задачи
    # доступен скрипту сразу. И обратно: напечатав ссылку на задачу, команда обязана
    # уметь её дождаться — иначе `--wait` у неё просто забыли.
    assert mismatched == {}
