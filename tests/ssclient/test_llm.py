import datetime

import pytest

from ssclient.llm.entities import LlmUsageGroupBy
from ssclient.llm.ids import LlmAccessKeyId, LlmGroupId, LlmModelId
from ssclient.llm.llm import LlmService
from ssclient.llm.usage import LlmUsageQuery
from ssclient.task_entities import TaskState
from tests.conftest import FakeRequest, task_response

LLM_PATH = 'api/v1/llm'
CONNECTION_PATH = '{llm}/connection'.format(llm=LLM_PATH)
GROUPS_PATH = '{llm}/groups'.format(llm=LLM_PATH)
ACCESS_KEYS_PATH = '{llm}/access-keys'.format(llm=LLM_PATH)
MODELS_PATH = '{llm}/models'.format(llm=LLM_PATH)
USAGE_PATH = '{llm}/usage'.format(llm=LLM_PATH)

GROUP_ID = LlmGroupId(5)
ACCESS_KEY_ID = LlmAccessKeyId(17)
MODEL_ID = LlmModelId(3)

GROUP_PATH = '{groups}/{group_id}'.format(groups=GROUPS_PATH, group_id=GROUP_ID)
GROUP_KEYS_PATH = '{group}/access-keys'.format(group=GROUP_PATH)
ACCESS_KEY_PATH = '{keys}/{access_key_id}'.format(keys=GROUP_KEYS_PATH, access_key_id=ACCESS_KEY_ID)

TASK_ID = 'llm12'
TASK_PATH = 'api/v1/tasks/{task_id}'.format(task_id=TASK_ID)
TASK_REFERENCE = {'task_id': TASK_ID}

# Формы провода cloudmng: поля без значения publisher не отдаёт вовсе, поэтому группа
# в создании и ключ в выпуске приходят без `id` и `state`, а сущности без необязательных
# полей — только с обязательными. Сервис снимает конверт и отдаёт сущность как есть.
CONNECTION = {'state': 'not_connected'}

GROUP_IN_CREATION = {'name': 'bots', 'created_at': '2026-11-01T10:00:00Z', 'task_id': TASK_ID}

GROUP = {
    'id': 5,
    'name': 'bots',
    'state': 'active',
    'tags': ['prod'],
    'models': [{'model_id': 3, 'tech_title': 'qwen3', 'name': 'Qwen 3'}],
    'created_at': '2026-11-01T10:00:00Z',
}

GROUP_SUSPENDED = dict(GROUP, id=6, state='suspended_by_project_quota')

GROUP_DETAILS = dict(
    GROUP,
    deployment_state='deployed',
    spend={'today': {'credits': 0}, 'week': {'credits': 1.5}, 'month': {'credits': 2, 'cost': 3.4}},
    total_spent_credits=2,
    updated_at='2026-11-02T10:00:00Z',
)

ACCESS_KEY_IN_ISSUE = {
    'group_id': 5, 'name': 'ci', 'created_at': '2026-11-01T10:00:00Z', 'task_id': TASK_ID,
}

ACCESS_KEY = {
    'id': 17,
    'group_id': 5,
    'name': 'ci',
    'state': 'active',
    'locks': {
        'by_client': False, 'by_quota': False, 'by_admin': False, 'by_balance': False, 'by_platform': False,
    },
    'created_at': '2026-11-01T10:00:00Z',
}

ACCESS_KEY_SUSPENDED = dict(ACCESS_KEY, id=18, state='suspended_by_project_quota')

MODEL = {
    'id': 3,
    'tech_title': 'qwen3',
    'name': 'Qwen 3',
    'description': '',
    'vendor': 'Alibaba',
    'kind': 'text',
    'contour': 'local',
    'storage_countries': ['RU'],
    'is_pii_protected': True,
    'context_size': 32768,
    'unit_kind': 'tokens',
    'endpoint': 'https://llm.example/v1',
    'is_available_to_groups': True,
}

MODEL_CATALOG = {'models': [MODEL]}

MODEL_DETAILS = dict(MODEL, default_provider='local', prices=[], providers=[])

# Текущий пакет в режиме денег: цена, скидка и валюта есть; выбор при исчерпании и лимит
# у пакета и повтором на верхнем уровне.
CURRENT_PACKAGE = {
    'package': {
        'id': 7,
        'tech_title': 'start',
        'volume_credits': 1000,
        'discount_percent': 5,
        'price': 950,
        'period_from': '2026-11-01T00:00:00Z',
        'period_to': '2026-12-01T00:00:00Z',
        'auto_renew': True,
        'exhausted_package_mode': 'continue_pay_as_you_go',
        'pay_as_you_go_limit_credits': 300,
        'state': 'active',
    },
    'usage': {
        'period_from': '2026-11-01',
        'period_to': '2026-12-01',
        'total_credits': 0,
        'package_volume_credits': 1000,
        'in_package_credits': 0,
        'over_package_credits': 0,
    },
    'price_per_credit': 1,
    'currency': 'RUB',
    'packages_disabled': False,
    'exhausted_package_mode': 'continue_pay_as_you_go',
    'pay_as_you_go_limit_credits': 300,
}

# Режим кредитов: денег нет ни у пакета, ни у ответа; без пакета выбор — по умолчанию,
# лимита нет; LLM остановлен квотой проекта.
CURRENT_PACKAGE_IN_CREDITS = {
    'usage': {
        'period_from': '2026-11-01',
        'period_to': '2026-12-01',
        'total_credits': 700,
        'in_package_credits': 0,
        'over_package_credits': 700,
    },
    'packages_disabled': False,
    'exhausted_package_mode': 'continue_pay_as_you_go',
    'stop': {'stopped_at': '2026-11-07T10:00:00Z', 'reason': 'project_quota_exhausted', 'state': 'stopped'},
}

PACKAGE_PLAN = {
    'id': 1,
    'source': 'catalog',
    'tech_title': 'start',
    'description': '',
    'volume_credits': 1000,
    'discount_percent': 5,
    'price': 950,
    'currency': 'RUB',
    'current_month': {
        'period_from': '2026-11-08T00:00:00Z', 'period_to': '2026-12-01T00:00:00Z', 'volume_credits': 750, 'price': 712.5,
    },
}

# Индивидуальный план в режиме кредитов: id тот же, что у каталожного, план различает источник;
# ни цены, ни скидки, ни валюты, в том числе у текущего месяца.
PACKAGE_PLAN_IN_CREDITS = {
    'id': 1,
    'source': 'individual',
    'tech_title': 'team',
    'description': '',
    'volume_credits': 5000,
    'current_month': {
        'period_from': '2026-11-08T00:00:00Z', 'period_to': '2026-12-01T00:00:00Z', 'volume_credits': 3750,
    },
}

USAGE_TOTALS = {
    'credits': 0, 'local_credits': 0, 'external_credits': 0, 'in_tokens': 0, 'out_tokens': 0, 'cached_tokens': 0,
}

USAGE = {
    'from': '2026-11-01',
    'to': '2026-11-30',
    'group_by': 'none',
    'totals': USAGE_TOTALS,
    'items': [],
    'collection': {'state': 'not_collected'},
}

REQUEST_LOG = {'source_connected': False, 'requests': []}

SECRET = {'secret': 'sk-llm-1'}


def _service(fake_http_client) -> LlmService:
    return LlmService(fake_http_client)


# Чтения: метод, путь контракта, ответ publisher'а и то, что сервис из него отдаёт.
# Каталог моделей и журнал запросов — ответ целиком: рядом со списком в них лежат
# цена кредита и признак подключения источника.
_READ_CASES = (
    (lambda llm: llm.connection().get(), 'GET', CONNECTION_PATH, {'connection': CONNECTION}, CONNECTION),
    (
        lambda llm: llm.groups().list(),
        'GET', GROUPS_PATH, {'groups': [GROUP_IN_CREATION, GROUP, GROUP_SUSPENDED]}, [GROUP_IN_CREATION, GROUP, GROUP_SUSPENDED],
    ),
    (lambda llm: llm.groups().get(GROUP_ID), 'GET', GROUP_PATH, {'group': GROUP_DETAILS}, GROUP_DETAILS),
    (
        lambda llm: llm.access_keys().list(),
        'GET', ACCESS_KEYS_PATH,
        {'access_keys': [ACCESS_KEY_IN_ISSUE, ACCESS_KEY, ACCESS_KEY_SUSPENDED]},
        [ACCESS_KEY_IN_ISSUE, ACCESS_KEY, ACCESS_KEY_SUSPENDED],
    ),
    (
        lambda llm: llm.access_keys().list(GROUP_ID),
        'GET', '{keys}?group_id=5'.format(keys=ACCESS_KEYS_PATH), {'access_keys': [ACCESS_KEY]}, [ACCESS_KEY],
    ),
    (
        lambda llm: llm.access_keys().get(GROUP_ID, ACCESS_KEY_ID),
        'GET', ACCESS_KEY_PATH, {'access_key': ACCESS_KEY}, ACCESS_KEY,
    ),
    (
        lambda llm: llm.access_keys().reveal_secret(GROUP_ID, ACCESS_KEY_ID),
        'POST', '{key}/secret'.format(key=ACCESS_KEY_PATH), SECRET, SECRET,
    ),
    (lambda llm: llm.models().list(), 'GET', MODELS_PATH, MODEL_CATALOG, MODEL_CATALOG),
    (
        lambda llm: llm.models().get(MODEL_ID),
        'GET', '{models}/3'.format(models=MODELS_PATH), {'model': MODEL_DETAILS}, MODEL_DETAILS,
    ),
    (
        lambda llm: llm.package().get(),
        'GET', '{llm}/package'.format(llm=LLM_PATH), {'package': CURRENT_PACKAGE}, CURRENT_PACKAGE,
    ),
    (
        lambda llm: llm.package().get(),
        'GET', '{llm}/package'.format(llm=LLM_PATH),
        {'package': CURRENT_PACKAGE_IN_CREDITS}, CURRENT_PACKAGE_IN_CREDITS,
    ),
    (
        lambda llm: llm.package().plans(),
        'GET', '{llm}/package-plans'.format(llm=LLM_PATH),
        {'package_plans': [PACKAGE_PLAN, PACKAGE_PLAN_IN_CREDITS]}, [PACKAGE_PLAN, PACKAGE_PLAN_IN_CREDITS],
    ),
    (
        lambda llm: llm.usage().requests(),
        'GET', '{llm}/requests'.format(llm=LLM_PATH), REQUEST_LOG, REQUEST_LOG,
    ),
)


@pytest.mark.parametrize('operation,method,path,response,expected', _READ_CASES)
async def test_read_takes_the_entity_from_the_response_of_the_contract(
    fake_http_client, operation, method, path, response, expected,
):
    fake_http_client.on(method, path, response)

    entity = await operation(_service(fake_http_client))

    assert [(request.method, request.path) for request in fake_http_client.requests] == [(method, path)]
    assert entity == expected


# Изменения без `--wait`: тело запроса контракта и ссылка на задачу как она пришла.
# У операций без тела publisher тела не ждёт — запрос уходит с `None`, а не с `{}`;
# у блокировки ключа тело есть всегда, причина — только когда задана.
_TASK_OPERATION_CASES = (
    (
        lambda llm: llm.connection().connect(group_name='bots', first_key_name='ci'),
        FakeRequest('POST', CONNECTION_PATH, {'group_name': 'bots', 'first_key_name': 'ci'}),
    ),
    (lambda llm: llm.groups().create(name='bots'), FakeRequest('POST', GROUPS_PATH, {'name': 'bots'})),
    (
        lambda llm: llm.groups().set_models(GROUP_ID, model_ids=(MODEL_ID, LlmModelId(4))),
        FakeRequest('PUT', '{group}/models'.format(group=GROUP_PATH), {'model_ids': [3, 4]}),
    ),
    (
        lambda llm: llm.groups().set_models(GROUP_ID, model_ids=()),
        FakeRequest('PUT', '{group}/models'.format(group=GROUP_PATH), {'model_ids': []}),
    ),
    (
        lambda llm: llm.groups().disable(GROUP_ID),
        FakeRequest('POST', '{group}/disable'.format(group=GROUP_PATH), None),
    ),
    (
        lambda llm: llm.access_keys().issue(GROUP_ID, name='ci'),
        FakeRequest('POST', GROUP_KEYS_PATH, {'name': 'ci'}),
    ),
    (
        lambda llm: llm.access_keys().lock(GROUP_ID, ACCESS_KEY_ID),
        FakeRequest('POST', '{key}/lock'.format(key=ACCESS_KEY_PATH), {}),
    ),
    (
        lambda llm: llm.access_keys().lock(GROUP_ID, ACCESS_KEY_ID, reason='leaked'),
        FakeRequest('POST', '{key}/lock'.format(key=ACCESS_KEY_PATH), {'reason': 'leaked'}),
    ),
    (
        lambda llm: llm.access_keys().unlock(GROUP_ID, ACCESS_KEY_ID),
        FakeRequest('POST', '{key}/unlock'.format(key=ACCESS_KEY_PATH), None),
    ),
    (
        lambda llm: llm.access_keys().delete(GROUP_ID, ACCESS_KEY_ID),
        FakeRequest('DELETE', ACCESS_KEY_PATH, None),
    ),
)


@pytest.mark.parametrize('operation,expected_request', _TASK_OPERATION_CASES)
async def test_operation_without_wait_returns_the_reference_to_the_task(
    fake_http_client, operation, expected_request,
):
    fake_http_client.on(expected_request.method, expected_request.path, TASK_REFERENCE)

    task_wrap = await operation(_service(fake_http_client))

    assert fake_http_client.requests == [expected_request]
    assert task_wrap == TASK_REFERENCE


# Теги заменяются набором целиком и сразу, без задачи: ответ publisher'а пуст.
_TAGS_CASES = (
    (lambda llm: llm.groups().set_tags(GROUP_ID, tags=('prod', 'ml')), '{group}/tags'.format(group=GROUP_PATH)),
    (
        lambda llm: llm.access_keys().set_tags(GROUP_ID, ACCESS_KEY_ID, tags=('prod', 'ml')),
        '{key}/tags'.format(key=ACCESS_KEY_PATH),
    ),
)


@pytest.mark.parametrize('operation,path', _TAGS_CASES)
async def test_set_tags_puts_the_whole_set_of_tags(fake_http_client, operation, path):
    fake_http_client.on('PUT', path, None)

    result = await operation(_service(fake_http_client))

    assert fake_http_client.requests == [FakeRequest('PUT', path, {'tags': ['prod', 'ml']})]
    assert result is None


def _completed_task(fake_http_client, method, path, resources=()):
    fake_http_client.on(method, path, TASK_REFERENCE)
    fake_http_client.on('GET', TASK_PATH, task_response(TASK_ID, TaskState.completed, resources))


# Созданная сущность адресуется ресурсом задачи своего типа: id чужого типа рядом
# не должен быть взят вместо него.
async def test_create_group_with_wait_reads_the_group_of_the_task(fake_http_client):
    _completed_task(
        fake_http_client, 'POST', GROUPS_PATH, resources=[('llm_access_key', '99'), ('llm_group', '5')],
    )
    fake_http_client.on('GET', GROUP_PATH, {'group': GROUP_DETAILS})

    group = await _service(fake_http_client).groups().create(name='bots', wait=True)

    assert fake_http_client.paths('GET') == [TASK_PATH, GROUP_PATH]
    assert group == GROUP_DETAILS


async def test_issue_access_key_with_wait_reads_the_key_of_the_task(fake_http_client):
    _completed_task(
        fake_http_client, 'POST', GROUP_KEYS_PATH, resources=[('llm_group', '5'), ('llm_access_key', '17')],
    )
    fake_http_client.on('GET', ACCESS_KEY_PATH, {'access_key': ACCESS_KEY})

    access_key = await _service(fake_http_client).access_keys().issue(GROUP_ID, name='ci', wait=True)

    assert fake_http_client.paths('GET') == [TASK_PATH, ACCESS_KEY_PATH]
    assert access_key == ACCESS_KEY


# Изменение известной сущности после задачи перечитывает её саму: задача ресурсов не несёт.
_WAIT_REREAD_CASES = (
    (
        lambda llm: llm.connection().connect(group_name='bots', first_key_name='ci', wait=True),
        'POST', CONNECTION_PATH, CONNECTION_PATH, {'connection': CONNECTION}, CONNECTION,
    ),
    (
        lambda llm: llm.groups().set_models(GROUP_ID, model_ids=(MODEL_ID,), wait=True),
        'PUT', '{group}/models'.format(group=GROUP_PATH), GROUP_PATH, {'group': GROUP_DETAILS}, GROUP_DETAILS,
    ),
    (
        lambda llm: llm.groups().disable(GROUP_ID, wait=True),
        'POST', '{group}/disable'.format(group=GROUP_PATH), GROUP_PATH, {'group': GROUP_DETAILS}, GROUP_DETAILS,
    ),
    (
        lambda llm: llm.access_keys().lock(GROUP_ID, ACCESS_KEY_ID, wait=True),
        'POST', '{key}/lock'.format(key=ACCESS_KEY_PATH), ACCESS_KEY_PATH, {'access_key': ACCESS_KEY}, ACCESS_KEY,
    ),
    (
        lambda llm: llm.access_keys().unlock(GROUP_ID, ACCESS_KEY_ID, wait=True),
        'POST', '{key}/unlock'.format(key=ACCESS_KEY_PATH), ACCESS_KEY_PATH, {'access_key': ACCESS_KEY}, ACCESS_KEY,
    ),
)


@pytest.mark.parametrize('operation,method,path,read_path,read_response,expected', _WAIT_REREAD_CASES)
async def test_operation_with_wait_rereads_the_changed_entity(
    fake_http_client, operation, method, path, read_path, read_response, expected,
):
    _completed_task(fake_http_client, method, path)
    fake_http_client.on('GET', read_path, read_response)

    entity = await operation(_service(fake_http_client))

    assert fake_http_client.paths('GET') == [TASK_PATH, read_path]
    assert entity == expected


async def test_delete_access_key_with_wait_polls_the_task_and_returns_nothing(fake_http_client):
    _completed_task(fake_http_client, 'DELETE', ACCESS_KEY_PATH)

    result = await _service(fake_http_client).access_keys().delete(GROUP_ID, ACCESS_KEY_ID, wait=True)

    assert fake_http_client.paths('GET') == [TASK_PATH]
    assert result is None


_PERIOD = {'period_from': datetime.date(2026, 11, 1), 'period_to': datetime.date(2026, 11, 30)}
_PERIOD_QUERY = 'from=2026-11-01&to=2026-11-30'

# Период уходит всегда, датами `YYYY-MM-DD`; разрез — строкой контракта; фильтр без
# значения в запрос не попадает, иначе publisher сузил бы расход до пустого.
_USAGE_QUERY_CASES = (
    ({}, _PERIOD_QUERY),
    ({'group_by': LlmUsageGroupBy.access_key}, '{period}&group_by=access_key'.format(period=_PERIOD_QUERY)),
    (
        {'group_id': GROUP_ID, 'access_key_id': ACCESS_KEY_ID, 'model_id': MODEL_ID},
        '{period}&group_id=5&access_key_id=17&model_id=3'.format(period=_PERIOD_QUERY),
    ),
)


@pytest.mark.parametrize('filters,expected_query', _USAGE_QUERY_CASES)
async def test_usage_sends_the_period_and_only_given_filters(fake_http_client, filters, expected_query):
    expected_path = '{usage}?{query}'.format(usage=USAGE_PATH, query=expected_query)
    fake_http_client.on('GET', expected_path, {'usage': USAGE})

    usage = await _service(fake_http_client).usage().usage(LlmUsageQuery(**_PERIOD, **filters))

    assert fake_http_client.paths('GET') == [expected_path]
    assert usage == USAGE
