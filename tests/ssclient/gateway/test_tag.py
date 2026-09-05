import pytest

from ssclient.gateway.tag import TagService
from tests.conftest import FakeRequest
from tests.ssclient.gateway.coordinates import GATEWAY_PATH

TAGS_PATH = '{gateway_path}/tags'.format(gateway_path=GATEWAY_PATH)


async def test_add_tag_posts_name_as_value(fake_http_client, gateway_id):
    fake_http_client.on('POST', TAGS_PATH, {'value': 'prod'})

    tag = await TagService(fake_http_client, gateway_id).create(name='prod')

    assert fake_http_client.requests == [FakeRequest('POST', TAGS_PATH, {'value': 'prod'})]
    assert tag == {'value': 'prod'}


@pytest.mark.parametrize('name,expected_segment', (
    ('prod', 'prod'),
    # Тег — последний сегмент пути (`tags/{**tag}`), publisher декодирует его сам:
    # незакодированный разделитель увёл бы удаление на чужой маршрут.
    ('team/prod', 'team%2Fprod'),
))
async def test_delete_tag_percent_encodes_name_in_path(
    fake_http_client, gateway_id, name, expected_segment,
):
    expected_path = '{tags_path}/{segment}'.format(tags_path=TAGS_PATH, segment=expected_segment)
    fake_http_client.on('DELETE', expected_path, None)

    await TagService(fake_http_client, gateway_id).delete(name)

    assert fake_http_client.requests == [FakeRequest('DELETE', expected_path)]
