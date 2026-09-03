import pytest

from ssclient import errors
from ssclient.task_id import TaskId

# Часть локации в vStack-id может быть пустой — маршрут publisher'а `^l\d*t\d+$`,
# поэтому `lt345` это валидный id, а не мусор.
# `already_completed_task` — синтетический id синхронных операций: реальной задачи нет,
# но клиент опрашивает её так же, как асинхронную.
SUPPORTED_IDS = (
    ('l2t345', False),
    ('lt345', False),
    ('dns42', False),
    ('vmw7', False),
    ('already_completed_task', True),
)

# `k8s_m1` / `k8s_f1` — точка расширения реестра, но услуга вне объёма задачи:
# пока записи в реестре нет, такой id обязан отвергаться, а не разбираться «как-нибудь».
UNSUPPORTED_IDS = (
    'k8s_m1',
    'k8s_f1',
    't42',
    'l2t',
    'dns',
    'vmw1x',
    'already_completed_task2',
    'garbage',
    '',
)


@pytest.mark.parametrize('raw_id,is_always_completed', SUPPORTED_IDS)
def test_supported_format_is_parsed(raw_id, is_always_completed):
    task_id = TaskId.parse(raw_id)

    assert task_id.value == raw_id
    assert task_id.is_always_completed is is_always_completed
    assert TaskId.try_parse(raw_id) == task_id


@pytest.mark.parametrize('raw_id', UNSUPPORTED_IDS)
def test_unsupported_format_is_rejected_by_both_factories(raw_id):
    assert TaskId.try_parse(raw_id) is None

    with pytest.raises(errors.UnknownTaskIdError) as exc_info:
        TaskId.parse(raw_id)

    assert exc_info.value.task_id == raw_id
