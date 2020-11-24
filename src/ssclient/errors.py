from typing import Any


class HttpClientError(Exception):
    """HttpClientError is a base error of HttpClient."""


class HttpClientResponseError(HttpClientError):
    def __init__(self, status: int, message: Any) -> None:
        super().__init__(status, message)
        self.status = status
        self.message = message


class TaskFailedError(Exception):
    def __init__(self, task_id: str) -> None:
        super().__init__("task '{task_id}' failed".format(task_id=task_id))
        self.task_id = task_id
