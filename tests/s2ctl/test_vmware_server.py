import pytest
from click.testing import CliRunner

from s2ctl import cmd_vmware
from s2ctl.entrypoint import entry_point
from ssclient.client import SSClient
from tests.ssclient.vmware.conftest import SERVER_ID, SERVER_PATH, SERVERS_PATH

_USAGE_ERROR_EXIT_CODE = 2

POWER_PATH = '{server_path}/power'.format(server_path=SERVER_PATH)

# Каждый переход питания — своя команда: пять команд бьют в пять маршрутов. Легаси-раздел
# vStack склеивает пары флагом `--hard`, здесь такой склейки нет и заводить её нельзя.
POWER_COMMANDS = (
    ('power-on', '{path}/on'.format(path=POWER_PATH)),
    ('power-off', '{path}/off'.format(path=POWER_PATH)),
    ('shutdown', '{path}/shutdown'.format(path=POWER_PATH)),
    ('reboot', '{path}/reboot'.format(path=POWER_PATH)),
    ('reset', '{path}/reset'.format(path=POWER_PATH)),
)

_CREATE_ARGS = (
    '--location', '1',
    '--name', 'srv',
    '--image', '5',
    '--cpu', '2',
    '--ram', '4096',
    '--system-disk-size', '51200',
)


@pytest.fixture
def cli_http_client(monkeypatch, fake_http_client):
    """Группа `vmware` строит сервис фабрикой клиента — подменяется она, а не сам сервис."""
    monkeypatch.setattr(cmd_vmware, 'client_factory', lambda _ctx: SSClient(fake_http_client))
    return fake_http_client


def _invoke(*args):
    return CliRunner().invoke(entry_point, ('-k', '02dadsd', 'vmware', 'server') + args)


@pytest.mark.parametrize('command_name,expected_path', POWER_COMMANDS)
def test_each_power_command_hits_its_own_route(cli_http_client, command_name, expected_path):
    cli_http_client.on('POST', expected_path, {'task_id': 'vmw55'})

    result = _invoke(command_name, str(SERVER_ID))

    assert result.exit_code == 0, result.output
    assert cli_http_client.paths('POST') == [expected_path]


@pytest.mark.parametrize('command_name', ('power-off', 'reboot'))
def test_power_commands_have_no_hard_flag(cli_config, command_name):
    result = CliRunner().invoke(
        entry_point, ('-k', '02dadsd', 'vmware', 'server', command_name, str(SERVER_ID), '--hard'),
    )

    # Обесточить и погасить гостевую ОС — разные команды, а не одна с признаком жёсткости.
    assert result.exit_code == _USAGE_ERROR_EXIT_CODE
    assert '--hard' in result.output


def test_gpu_triple_is_sent_as_the_whole_profile(cli_http_client):
    cli_http_client.on('POST', SERVERS_PATH, {'server_id': 777, 'task_id': 'vmw11'})

    result = _invoke('create', *_CREATE_ARGS, '--gpu', '3:8192:1')

    assert result.exit_code == 0, result.output
    order_payload = cli_http_client.requests[0].payload
    assert order_payload['gpu'] == {'gpu_model_id': 3, 'vram_mb': 8192, 'card_count': 1}


def test_malformed_gpu_is_reported_as_bad_parameter(cli_config):
    result = CliRunner().invoke(entry_point, (
        '-k', '02dadsd', 'vmware', 'server', 'create',
    ) + _CREATE_ARGS + ('--gpu', '3:8192'))

    # Разбор тройки падает до запроса: пользователь видит формат, а не общую ошибку команды.
    assert result.exit_code == _USAGE_ERROR_EXIT_CODE
    assert 'MODEL_ID:VRAM_MB:CARD_COUNT' in result.output
