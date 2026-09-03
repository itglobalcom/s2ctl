from ssclient.server.price import ServerPriceService
from tests.conftest import FakeRequest

PRICE_PATH = 'api/v1/servers/price'


async def test_calculate_posts_configuration_and_returns_monthly_price(fake_http_client):
    fake_http_client.on('POST', PRICE_PATH, {'price': 3990.5})

    price = await ServerPriceService(fake_http_client).calculate(
        location_id='am2',
        image_id='img',
        cpu=2,
        ram_mb=4096,
        volumes=[10240, 20480],
        networks=[100],
    )

    assert price['price'] == 3990.5
    assert fake_http_client.requests == [FakeRequest('POST', PRICE_PATH, {
        'location_id': 'am2',
        'image_id': 'img',
        'cpu': 2,
        'ram_mb': 4096,
        'volumes': [{'size_mb': 10240}, {'size_mb': 20480}],
        'networks': [{'bandwidth_mbps': 100}],
    })]


async def test_price_without_public_networks_sends_null_instead_of_empty_list(fake_http_client):
    # Для publisher'а `null` и `[]` разные: на `null` он считает один публичный интерфейс
    # минимальной ширины локации, на пустой список — конфигурацию вовсе без сети.
    fake_http_client.on('POST', PRICE_PATH, {'price': 100})

    await ServerPriceService(fake_http_client).calculate(
        location_id='am2', image_id='img', cpu=1, ram_mb=1024, volumes=[10240],
    )

    assert fake_http_client.requests[0].payload['networks'] is None
