import pytest

from ssclient import errors
from ssclient.task_entities import TaskResourceType, task_resource_id


def test_resource_id_is_taken_by_resource_type():
    task = {
        'id': 'l2t345',
        'is_completed': 'Completed',
        'resources': [
            {'type': 'volume', 'id': '77'},
            {'type': 'server', 'id': 'l2s99'},
        ],
    }

    assert task_resource_id(task, TaskResourceType.server) == 'l2s99'
    assert task_resource_id(task, TaskResourceType.volume) == '77'


def test_missing_resource_type_is_reported_and_legacy_field_is_not_used():
    # legacy-поля вида `server_id` publisher помечает [Obsolete], а у VMware-задачи их нет
    # вовсе: единственный источник id ресурса — resources[].
    task = {
        'id': 'vmw7',
        'is_completed': 'Completed',
        'server_id': 'legacy-42',
        'resources': [{'type': 'network', 'id': '5'}],
    }

    with pytest.raises(errors.TaskResourceMissingError) as exc_info:
        task_resource_id(task, TaskResourceType.server)

    assert exc_info.value.task_id == 'vmw7'
    assert exc_info.value.resource_type == 'server'
