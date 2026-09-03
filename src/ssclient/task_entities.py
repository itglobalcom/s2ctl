from enum import Enum, unique
from typing import List, Optional, TypedDict

from ssclient import errors


@unique
class TaskState(Enum):
    """Статус задачи; publisher отдаёт его строкой в PascalCase."""

    new = 'New'
    in_progress = 'InProgress'
    completed = 'Completed'
    failed = 'Failed'
    canceled = 'Canceled'


@unique
class TaskResourceType(Enum):
    """Тип ресурса, затронутого задачей; закрытый словарь контракта."""

    server = 'server'
    network = 'network'
    volume = 'volume'
    snapshot = 'snapshot'
    nic = 'nic'
    gateway = 'gateway'
    domain = 'domain'
    record = 'record'
    ptr = 'ptr'
    cluster = 'cluster'


class TaskResourceEntity(TypedDict):
    type: str  # noqa: WPS125
    id: str  # noqa: WPS125


class TaskEntity(TypedDict, total=False):
    id: str  # noqa: WPS125
    type: str  # noqa: WPS125
    progress_percent: int
    is_completed: str
    created: str
    completed: Optional[str]
    resources: List[TaskResourceEntity]


def task_state(task: TaskEntity) -> TaskState:
    return TaskState(task['is_completed'])


def task_resource_id(task: TaskEntity, resource_type: TaskResourceType) -> str:
    """Id ресурса задачи в том формате, которым услуга адресует его в своих маршрутах.

    Источник — только `resources[]`: сервисные поля вида `server_id` publisher
    помечает deprecated, а у VMware-задачи их нет вовсе.
    """
    for resource in task.get('resources') or ():
        if resource['type'] == resource_type.value:
            return resource['id']
    raise errors.TaskResourceMissingError(task.get('id', ''), resource_type.value)


def completed_task(task_id: str) -> TaskEntity:
    return TaskEntity(
        id=task_id,
        is_completed=TaskState.completed.value,
        resources=[],
    )
