import pytest

from ssclient.server.server_id import ServerId

# Маршрут publisher'а — `^l\d+s\d+$`: обе части обязательны, порядок закреплён,
# поэтому перепутанные местами части (`s1l2`) — такой же мусор, как произвольная
# строка. Разбор обязан отвергнуть их до запроса, а не собрать путь, по которому
# publisher ответит 404.
ID_FORMATS = (
    ('l1s2', 'l1s2'),
    ('l12s345', 'l12s345'),
    ('s1l2', None),
    ('l1s', None),
    ('ls2', None),
    ('l1e2', None),
    ('l1s2x', None),
    ('xl1s2', None),
    ('garbage', None),
    ('', None),
)


@pytest.mark.parametrize('raw_id,expected_value', ID_FORMATS)
def test_composite_id_is_parsed_only_in_publisher_format(raw_id, expected_value):
    server_id = ServerId.try_parse(raw_id)

    if expected_value is None:
        assert server_id is None
    else:
        assert server_id is not None
        assert server_id.value == expected_value
