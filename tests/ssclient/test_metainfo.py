import pytest

from ssclient.metainfo import ApplicationsService, ImagesService, LocationsService

APPLICATIONS_PATH = 'api/v1/applications'

LOCATIONS_PATH = 'api/v1/locations'

IMAGES_PATH = 'api/v1/images'

# Формы `VstackLocation` и `VstackImage` контракта целиком: сервис снимает конверт
# ответа и отдаёт сущность как есть, ничего из неё не вычитая.
LOCATION_ENTITY = {
    'id': 'ds1',
    'system_volume_min': 25600,
    'additional_volume_min': 1024,
    'volume_max': 2048000,
    'windows_system_volume_min': 51200,
    'bandwidth_min': 10,
    'bandwidth_max': 1000,
    'cpu_quantity_options': [1, 2, 4],
    'ram_size_options': [512, 1024, 2048],
}

IMAGE_ENTITY = {
    'id': 'ds1i123',
    'location_id': 'ds1',
    'type': 'Ubuntu',
    'os_version': '22.04',
    'architecture': 'X64',
    'allow_ssh_keys': True,
}


async def test_locations_catalog_is_unwrapped(fake_http_client):
    fake_http_client.on('GET', LOCATIONS_PATH, {'locations': [LOCATION_ENTITY]})

    locations = await LocationsService(fake_http_client).get()

    assert fake_http_client.paths('GET') == [LOCATIONS_PATH]
    assert locations == [LOCATION_ENTITY]


async def test_images_catalog_is_unwrapped(fake_http_client):
    fake_http_client.on('GET', IMAGES_PATH, {'images': [IMAGE_ENTITY]})

    images = await ImagesService(fake_http_client).get()

    assert fake_http_client.paths('GET') == [IMAGES_PATH]
    assert images == [IMAGE_ENTITY]


async def test_images_catalog_is_filtered_by_the_location_of_the_contract(fake_http_client):
    expected_path = '{path}?location_id=ds1'.format(path=IMAGES_PATH)
    fake_http_client.on('GET', expected_path, {'images': [IMAGE_ENTITY]})

    await ImagesService(fake_http_client).get(location_id='ds1')

    assert fake_http_client.paths('GET') == [expected_path]


APPLICATION_ENTITY = {
    'id': 'docker',
    'location_id': 'am2',
    'images': ['ubuntu-22-04', 'debian-12'],
}


async def test_applications_catalog_is_unwrapped(fake_http_client):
    fake_http_client.on('GET', APPLICATIONS_PATH, {'applications': [APPLICATION_ENTITY]})

    applications = await ApplicationsService(fake_http_client).list()

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

    await ApplicationsService(fake_http_client).list(**filters)

    assert fake_http_client.paths('GET') == [expected_path]
