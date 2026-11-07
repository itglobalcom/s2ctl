"""Связка «опция CLI → поле запроса контракта» для раздела LLM."""
import json

import pytest
from click.testing import CliRunner

from s2ctl.entrypoint import entry_point
from tests.conftest import FakeRequest
from tests.s2ctl.conftest import APIKEY

_USAGE_ERROR_EXIT_CODE = 2

LLM_PATH = 'api/v1/llm'
GROUP_PATH = '{llm}/groups/5'.format(llm=LLM_PATH)
ACCESS_KEY_PATH = '{group}/access-keys/17'.format(group=GROUP_PATH)
USAGE_PATH = '{llm}/usage'.format(llm=LLM_PATH)

TASK_REFERENCE = {'task_id': 'llm12'}

# Имена опций и полей контракта расходятся: `--model` кладётся в `model_ids[]`, `--tag` —
# в `tags[]`, опущенная опция набора — пустой набор, который снимает всё.
_CONTRACT_FIELD_CASES = (
    (
        ('connect', '--group-name', 'bots', '--first-key-name', 'ci'),
        FakeRequest('POST', '{llm}/connection'.format(llm=LLM_PATH), {'group_name': 'bots', 'first_key_name': 'ci'}),
    ),
    (
        ('group', 'create', '--name', 'bots'),
        FakeRequest('POST', '{llm}/groups'.format(llm=LLM_PATH), {'name': 'bots'}),
    ),
    (
        ('group', 'set-models', '5', '--model', '3', '--model', '4'),
        FakeRequest('PUT', '{group}/models'.format(group=GROUP_PATH), {'model_ids': [3, 4]}),
    ),
    (
        ('group', 'set-models', '5'),
        FakeRequest('PUT', '{group}/models'.format(group=GROUP_PATH), {'model_ids': []}),
    ),
    (
        ('group', 'set-tags', '5', '--tag', 'prod', '--tag', 'ml'),
        FakeRequest('PUT', '{group}/tags'.format(group=GROUP_PATH), {'tags': ['prod', 'ml']}),
    ),
    (
        ('group', 'set-tags', '5'),
        FakeRequest('PUT', '{group}/tags'.format(group=GROUP_PATH), {'tags': []}),
    ),
    (
        ('key', 'issue', '5', '--name', 'ci'),
        FakeRequest('POST', '{group}/access-keys'.format(group=GROUP_PATH), {'name': 'ci'}),
    ),
    (
        ('key', 'lock', '5', '17', '--reason', 'leaked'),
        FakeRequest('POST', '{key}/lock'.format(key=ACCESS_KEY_PATH), {'reason': 'leaked'}),
    ),
    (
        ('key', 'lock', '5', '17'),
        FakeRequest('POST', '{key}/lock'.format(key=ACCESS_KEY_PATH), {}),
    ),
    (
        ('key', 'set-tags', '5', '17', '--tag', 'prod'),
        FakeRequest('PUT', '{key}/tags'.format(key=ACCESS_KEY_PATH), {'tags': ['prod']}),
    ),
)


def _invoke(*args):
    return CliRunner().invoke(entry_point, ('-k', APIKEY, 'llm') + args)


@pytest.mark.parametrize('command_args,expected_request', _CONTRACT_FIELD_CASES)
def test_command_options_reach_the_fields_of_the_contract(
    cli_http_client, command_args, expected_request,
):
    cli_http_client.on(expected_request.method, expected_request.path, TASK_REFERENCE)

    result = _invoke(*command_args)

    assert result.exit_code == 0, result.output
    assert cli_http_client.requests == [expected_request]


def test_key_list_passes_its_group_to_the_query_of_the_contract(cli_http_client):
    expected_path = '{llm}/access-keys?group_id=5'.format(llm=LLM_PATH)
    cli_http_client.on('GET', expected_path, {'access_keys': []})

    result = _invoke('key', 'list', '--group', '5')

    assert result.exit_code == 0, result.output
    assert cli_http_client.paths('GET') == [expected_path]


def test_key_secret_prints_the_secret(cli_http_client):
    cli_http_client.on('POST', '{key}/secret'.format(key=ACCESS_KEY_PATH), {'secret': 'sk-llm-1'})

    result = _invoke('key', 'secret', '5', '17', '--output', 'json')

    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == {'secret': 'sk-llm-1'}


_USAGE = {
    'from': '2026-11-01',
    'to': '2026-11-30',
    'group_by': 'model',
    'totals': {},
    'items': [],
    'collection': {'state': 'collected'},
}


# `--group`, `--key` и `--model` расхода кладутся в `group_id`, `access_key_id` и `model_id`.
def test_usage_options_reach_the_query_of_the_contract(cli_http_client):
    expected_path = '{usage}?from=2026-11-01&to=2026-11-30&group_by=model&group_id=5&access_key_id=17&model_id=3'.format(
        usage=USAGE_PATH,
    )
    cli_http_client.on('GET', expected_path, {'usage': _USAGE})

    result = _invoke(
        'usage', '--from', '2026-11-01', '--to', '2026-11-30', '--group-by', 'model',
        '--group', '5', '--key', '17', '--model', '3', '--output', 'json',
    )

    assert result.exit_code == 0, result.output
    assert cli_http_client.paths('GET') == [expected_path]
    assert json.loads(result.output) == _USAGE


# Период и разрез разбираются до запроса: publisher ждёт даты `YYYY-MM-DD` и разрез
# из своего перечня.
_REFUSED_USAGE_ARGS = (
    (('--from', '01.11.2026', '--to', '2026-11-30'), '--from'),
    (('--from', '2026-11-01'), '--to'),
    (('--from', '2026-11-01', '--to', '2026-11-30', '--group-by', 'week'), '--group-by'),
)


@pytest.mark.parametrize('usage_args,reported', _REFUSED_USAGE_ARGS)
def test_usage_refuses_a_period_or_split_out_of_the_contract(cli_http_client, usage_args, reported):
    result = _invoke('usage', *usage_args)

    assert result.exit_code == _USAGE_ERROR_EXIT_CODE
    assert reported in result.output
    assert cli_http_client.requests == []
