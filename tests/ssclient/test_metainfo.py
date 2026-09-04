import pytest

from ssclient.metainfo import ApplicationsService

APPLICATIONS_PATH = 'api/v1/applications'

APPLICATION_ENTITY = {
    'id': 'docker',
    'location_id': 'am2',
    'images': ['ubuntu-22-04', 'debian-12'],
}


async def test_applications_catalog_is_unwrapped(fake_http_client):
    fake_http_client.on('GET', APPLICATIONS_PATH, {'applications': [APPLICATION_ENTITY]})

    applications = await ApplicationsService(fake_http_client).get()

    assert fake_http_client.paths('GET') == [APPLICATIONS_PATH]
    assert applications == [APPLICATION_ENTITY]


# Все три фильтра каталога приложений publisher принимает строками и по отдельности:
# `location_id` разворачивается в перечисление локаций, `application_id` и `image_id`
# сверяются на точное совпадение.
_FILTER_CASES = (
    ({}, APPLICATIONS_PATH),
    ({'location_id': 'am2'}, '{path}?location_id=am2'.format(path=APPLICATIONS_PATH)),
    ({'application_id': 'docker'}, '{path}?application_id=docker'.format(path=APPLICATIONS_PATH)),
    ({'image_id': 'ubuntu-22-04'}, '{path}?image_id=ubuntu-22-04'.format(path=APPLICATIONS_PATH)),
)


@pytest.mark.parametrize('filters,expected_path', _FILTER_CASES)
async def test_applications_catalog_is_filtered_by_the_query_of_the_contract(
    fake_http_client, filters, expected_path,
):
    fake_http_client.on('GET', expected_path, {'applications': [APPLICATION_ENTITY]})

    await ApplicationsService(fake_http_client).get(**filters)

    assert fake_http_client.paths('GET') == [expected_path]
