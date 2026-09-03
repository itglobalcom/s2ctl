from typing import ClassVar

from ssclient.base import TASKS_PATH, BaseService, task_path
from ssclient.task_entities import TaskEntity
from ssclient.task_id import TaskId


class TaskService(BaseService):
    _path: ClassVar[str] = TASKS_PATH

    async def get(self, task_id: TaskId) -> TaskEntity:
        task_resp = await self._http_client.get(task_path(task_id))
        return task_resp['task']
