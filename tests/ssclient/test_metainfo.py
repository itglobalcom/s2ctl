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
