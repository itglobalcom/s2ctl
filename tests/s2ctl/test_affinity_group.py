import pytest
from click.testing import CliRunner

from s2ctl.entrypoint import entry_point
from ssclient.affinity_group_id import AFFINITY_GROUP_ID_TEMPLATE
from tests.conftest import FakeRequest

_USAGE_ERROR_EXIT_CODE = 2

RAW_GROUP_ID = 'l1g2'
GROUPS_PATH = 'api/v1/affinity-groups'
GROUP_PATH = '{path}/{group_id}'.format(path=GROUPS_PATH, group_id=RAW_GROUP_ID)

GROUP_ENTITY = {
    'id': RAW_GROUP_ID,
    'location_id': 'l1',
    'name': 'web',
    'affinity': True,
    'server_ids': [],
}

# Род группы publisher принимает булевым полем `affinity`, а команда — парой флагов:
# держать серверы вместе и разносить их по хостам — не значение свободной строки.
_GROUP_KINDS = (
    ('--affinity', True),
    ('--anti-affinity', False),
)


def _invoke(*args):
    return CliRunner().invoke(entry_point, ('-k', '02dadsd', 'affinity-group') + args)


# cli_config — autouse, объявлена явно: без неё прогон пишет конфиг и keyring в домашний каталог.
def test_malformed_group_id_is_reported_as_bad_parameter(cli_config):
    result = _invoke('get', 'g1l2')

    assert result.exit_code == _USAGE_ERROR_EXIT_CODE
    # Разбор id падает до запроса: пользователь видит формат id, а не traceback.
    assert AFFINITY_GROUP_ID_TEMPLATE in result.output
    assert result.exc_info[0] is SystemExit


@pytest.mark.parametrize('kind_flag,expected_affinity', _GROUP_KINDS)
def test_create_maps_the_kind_of_the_group_to_the_field_of_the_contract(
    cli_http_client, kind_flag, expected_affinity,
):
    cli_http_client.on('POST', GROUPS_PATH, {'affinity_group': GROUP_ENTITY})

    result = _invoke('create', '--location', 'am2', '--name', 'web', kind_flag)

    assert result.exit_code == 0, result.output
    assert cli_http_client.requests == [FakeRequest('POST', GROUPS_PATH, {
        'location_id': 'am2',
        'name': 'web',
        'affinity': expected_affinity,
    })]


def test_delete_asks_the_publisher_for_the_reference_to_the_task(cli_http_client):
    # Без `return_task=true` ответ удаления пуст, и `--wait` нечего ждать.
    expected_path = '{path}?return_task=true'.format(path=GROUP_PATH)
    cli_http_client.on('DELETE', expected_path, {'task_id': 'already_completed_task'})

    result = _invoke('delete', RAW_GROUP_ID)

    assert result.exit_code == 0, result.output
    assert cli_http_client.paths('DELETE') == [expected_path]


def test_list_passes_the_location_to_the_query_of_the_contract(cli_http_client):
    expected_path = '{path}?location_id=am2'.format(path=GROUPS_PATH)
    cli_http_client.on('GET', expected_path, {'affinity_groups': [GROUP_ENTITY]})

    result = _invoke('list', '--location', 'am2')

    assert result.exit_code == 0, result.output
    assert cli_http_client.paths('GET') == [expected_path]
