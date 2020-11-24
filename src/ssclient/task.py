from ssclient.base import BaseService, TaskEntity


class TaskService(BaseService):
    path = 'api/v1/tasks'

    async def get(self, task_id: str) -> TaskEntity:
        path = self._task_path(task_id)
        task_resp = await self._http_client.get(path)
        return task_resp['task']

    def _task_path(self, task_id: str):
        return '{path}/{task_id}'.format(path=self.path, task_id=task_id)
