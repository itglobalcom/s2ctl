import pytest

from ssclient.gateway.gateway_id import GatewayId
from tests.ssclient.gateway.coordinates import RAW_GATEWAY_ID


@pytest.fixture
def gateway_id() -> GatewayId:
    parsed_id = GatewayId.try_parse(RAW_GATEWAY_ID)
    assert parsed_id is not None
    return parsed_id
