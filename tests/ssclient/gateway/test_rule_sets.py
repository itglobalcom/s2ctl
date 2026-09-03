import pytest

from ssclient.gateway.firewall import FirewallService
from ssclient.gateway.nat import NatService
from ssclient.task_entities import TaskState
from tests.conftest import FakeRequest, task_response
from tests.ssclient.gateway.conftest import GATEWAY_PATH

FIREWALL_RULE = {
    'action': 'allow',
    'direction': 'in',
    'protocol': 'tcp',
    'source': '0.0.0.0/0',
    'source_port': 0,
    'destination': '10.0.0.1',
    'destination_port': 443,
}

NAT_RULE = {
    'type': 'dnat',
    'protocol': 'tcp',
    'source': '0.0.0.0/0',
    'destination': '203.0.113.1',
    'destination_port': 443,
    'translated': '10.0.0.1',
    'translated_port': 443,
}

# Два набора правил шлюза устроены одинаково: свой подресурс, чтение отдаёт список
# под своим ключом, запись заменяет набор целиком (частичного изменения в контракте нет).
RULE_SETS = (
    (FirewallService, '{gateway}/firewall'.format(gateway=GATEWAY_PATH), 'firewall_rules',
     FIREWALL_RULE),
    (NatService, '{gateway}/nat'.format(gateway=GATEWAY_PATH), 'nat_rules', NAT_RULE),
)


@pytest.mark.parametrize('service_class,path,rules_key,rule', RULE_SETS)
async def test_get_unwraps_rule_set(fake_http_client, gateway_id, service_class, path, rules_key, rule):
    fake_http_client.on('GET', path, {rules_key: [rule]})

    rules = await service_class(fake_http_client, gateway_id).get()

    assert fake_http_client.paths('GET') == [path]
    assert rules == [rule]


@pytest.mark.parametrize('service_class,path,rules_key,rule', RULE_SETS)
async def test_replace_puts_whole_rule_set_and_returns_task_without_wait(
    fake_http_client, gateway_id, service_class, path, rules_key, rule,
):
    fake_http_client.on('PUT', path, {'task_id': 'l1t345'})

    task_wrap = await service_class(fake_http_client, gateway_id).replace([rule])

    assert fake_http_client.requests == [FakeRequest('PUT', path, {rules_key: [rule]})]
    assert task_wrap == {'task_id': 'l1t345'}


@pytest.mark.parametrize('service_class,path,rules_key,rule', RULE_SETS)
async def test_replace_with_wait_polls_task_and_returns_nothing(
    fake_http_client, gateway_id, service_class, path, rules_key, rule,
):
    fake_http_client.on('PUT', path, {'task_id': 'l1t345'})
    fake_http_client.on('GET', 'api/v1/tasks/l1t345', task_response('l1t345', TaskState.completed))

    task_wrap = await service_class(fake_http_client, gateway_id).replace([rule], wait=True)

    assert fake_http_client.paths('GET') == ['api/v1/tasks/l1t345']
    assert task_wrap is None
