import pytest

from ssclient.affinity_group import AffinityGroupService
from ssclient.affinity_group_id import AffinityGroupId
from tests.conftest import FakeRequest

GROUPS_PATH = 'api/v1/affinity-groups'
GROUP_PATH = 'api/v1/affinity-groups/l1g2'

# Маршрут publisher'а — `^l\d+g\d+$`: части id обязательны, порядок закреплён,
# и перепутанные местами части (`g1l2`) — такой же мусор, как произвольная строка.
ID_FORMATS = (
    ('l1g2', 'l1g2'),
    ('l12g345', 'l12g345'),
    ('g1l2', None),
    ('l1g', None),
    ('lg2', None),
    ('l1s2', None),
    ('l1g2x', None),
    ('garbage', None),
    ('', None),
)

GROUP_ENTITY = {
    'id': 'l1g2',
    'location_id': 'l1',
    'name': 'web',
    'affinity': False,
    'server_ids': ['l1s7'],
}


def _group_id(raw_id: str) -> AffinityGroupId:
    group_id = AffinityGroupId.try_parse(raw_id)
    assert group_id is not None
    return group_id


@pytest.mark.parametrize('raw_id,expected_value', ID_FORMATS)
def test_composite_id_is_parsed_only_in_publisher_format(raw_id, expected_value):
    group_id = AffinityGroupId.try_parse(raw_id)

    if expected_value is None:
        assert group_id is None
    else:
        assert group_id is not None
        assert group_id.value == expected_value


async def test_create_posts_group_and_unwraps_entity(fake_http_client):
    fake_http_client.on('POST', GROUPS_PATH, {'affinity_group': GROUP_ENTITY})

    group = await AffinityGroupService(fake_http_client).create(
        location_id='l1', name='web', affinity=False,
    )

    assert fake_http_client.requests == [FakeRequest('POST', GROUPS_PATH, {
        'location_id': 'l1',
        'name': 'web',
        'affinity': False,
    })]
    assert group == GROUP_ENTITY


async def test_list_unwraps_groups(fake_http_client):
    fake_http_client.on('GET', GROUPS_PATH, {'affinity_groups': [GROUP_ENTITY]})

    groups = await AffinityGroupService(fake_http_client).list()

    assert fake_http_client.paths('GET') == [GROUPS_PATH]
    assert groups == [GROUP_ENTITY]


async def test_get_reads_group_by_composite_id(fake_http_client):
    fake_http_client.on('GET', GROUP_PATH, {'affinity_group': GROUP_ENTITY})

    group = await AffinityGroupService(fake_http_client).get(_group_id('l1g2'))

    assert fake_http_client.paths('GET') == [GROUP_PATH]
    assert group == GROUP_ENTITY


async def test_delete_without_wait_returns_synthetic_completed_task(fake_http_client):
    # Ссылку на задачу publisher отдаёт только по `return_task=true`; удаление группы
    # синхронное, поэтому задача синтетическая — но команде она нужна так же,
    # как настоящая: без неё вывод удаления пуст.
    delete_path = '{path}?return_task=true'.format(path=GROUP_PATH)
    fake_http_client.on('DELETE', delete_path, {'task_id': 'already_completed_task'})

    task_wrap = await AffinityGroupService(fake_http_client).delete(_group_id('l1g2'))

    assert fake_http_client.requests == [FakeRequest('DELETE', delete_path)]
    assert task_wrap == {'task_id': 'already_completed_task'}


async def test_delete_with_wait_does_not_poll_synthetic_task(fake_http_client):
    delete_path = '{path}?return_task=true'.format(path=GROUP_PATH)
    fake_http_client.on('DELETE', delete_path, {'task_id': 'already_completed_task'})

    task_wrap = await AffinityGroupService(fake_http_client).delete(_group_id('l1g2'), wait=True)

    assert fake_http_client.requests == [FakeRequest('DELETE', delete_path)]
    assert fake_http_client.paths('GET') == []
    assert task_wrap is None
