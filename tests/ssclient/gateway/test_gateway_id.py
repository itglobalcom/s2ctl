import pytest

from ssclient.gateway.gateway_id import GatewayId

# Маршрут publisher'а — `l{location_id}e{gateway_id}`: обе части обязательны, порядок
# закреплён, поэтому перепутанные местами части (`e1l2`) — такой же мусор, как
# произвольная строка. Разбор обязан отвергнуть их до запроса, а не собрать путь,
# по которому publisher ответит 404.
ID_FORMATS = (
    ('l1e2', 'l1e2'),
    ('l12e345', 'l12e345'),
    ('e1l2', None),
    ('l1e', None),
    ('le2', None),
    ('l1s2', None),
    ('l1e2x', None),
    ('xl1e2', None),
    ('garbage', None),
    ('', None),
)


@pytest.mark.parametrize('raw_id,expected_value', ID_FORMATS)
def test_composite_id_is_parsed_only_in_publisher_format(raw_id, expected_value):
    gateway_id = GatewayId.try_parse(raw_id)

    if expected_value is None:
        assert gateway_id is None
    else:
        assert gateway_id is not None
        assert gateway_id.value == expected_value
