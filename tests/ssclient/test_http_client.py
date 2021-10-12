import pytest

from ssclient import errors
from ssclient.http_client import HttpClient

TESTS_PAYLOAD = (
    {},
    {'user': 'mrd'},
    {'user': 'mrd', 'some_bool_field': True, 'some_none_field': None},
)

TEST_APIKEY = 'apikey'


@pytest.mark.parametrize('apikey', [None, 'test_apikey'])
@pytest.mark.parametrize('path', ['first', '/first', 'first/second', '/first/second'])
async def test_apikey(apikey, path, http_client):
    client: HttpClient = http_client(apikey)
    server_answer = await client.get(path)
    if apikey:
        assert server_answer['headers'].get('X-API-KEY') == apikey
    else:
        assert 'X-API-KEY' not in server_answer['headers']
    # path checking
    if not path.startswith('/'):
        path = '/{path}'.format(path=path)
    assert server_answer['path'] == path
    # payload checking
    assert server_answer['payload'] == ''


@pytest.mark.parametrize('payload', TESTS_PAYLOAD)
async def test_post_method(payload, http_client):
    path = '/post'
    client: HttpClient = http_client(TEST_APIKEY)
    server_answer = await client.post(path, payload)

    assert server_answer['method'] == 'GET'
    assert server_answer['path'] == path
    assert server_answer['payload'] == payload


@pytest.mark.parametrize('payload', TESTS_PAYLOAD)
async def test_post_method(payload, http_client):
    path = '/post'
    client: HttpClient = http_client(TEST_APIKEY)
    server_answer = await client.post(path, payload)

    assert server_answer['method'] == 'POST'
    assert server_answer['path'] == path
    assert server_answer['payload'] == payload


@pytest.mark.parametrize('payload', TESTS_PAYLOAD)
async def test_put_method(payload, http_client):
    path = '/put'
    client: HttpClient = http_client(TEST_APIKEY)
    server_answer = await client.put(path, payload)

    assert server_answer['method'] == 'PUT'
    assert server_answer['path'] == path
    assert server_answer['payload'] == payload


async def test_delete_method(http_client):
    path = '/delete'
    client: HttpClient = http_client(TEST_APIKEY)
    server_answer = await client.delete(path)

    assert server_answer['method'] == 'DELETE'
    assert server_answer['path'] == path
    assert server_answer['payload'] == ''


async def test_request_error(http_client):
    status = 401
    path = '/error/{status}'.format(status=status)
    client: HttpClient = http_client(TEST_APIKEY)
    with pytest.raises(errors.HttpClientResponseError) as exc_info:
        await client.post(path, {})
        assert exc_info.value.status == status


@pytest.mark.parametrize(
    'apikey,headers',
    [
        ('test_apikey', {
            'X-API-KEY': 'test_apikey',
            'User-Agent': 's2ctl',
        }),
        (None, {'User-Agent': 's2ctl'}),
    ],
)
def test_request_headers(apikey, headers):
    client = HttpClient(host='', apikey=apikey)
    assert client.headers == headers
