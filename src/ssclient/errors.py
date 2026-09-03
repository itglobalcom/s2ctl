from typing import Any


class HttpClientError(Exception):
    """HttpClientError is a base error of HttpClient."""


class HttpClientResponseError(HttpClientError):
    def __init__(self, status: int, message: Any) -> None:
        super().__init__(status, message)
        self.status = status
        self.message = message


class UnknownTaskIdError(Exception):
    def __init__(self, task_id: str, supported_formats: str) -> None:
        super().__init__(
            "unknown task id '{task_id}'; supported formats: {supported_formats}".format(
                task_id=task_id, supported_formats=supported_formats,
            ),
        )
        self.task_id = task_id


class TaskFailedError(Exception):
    def __init__(self, task_id: str, state: str) -> None:
        super().__init__(
            "task '{task_id}' finished with state '{state}'".format(
                task_id=task_id, state=state,
            ),
        )
        self.task_id = task_id
        self.state = state


class TaskWaitTimeoutError(TimeoutError):
    def __init__(self, task_id: str, timeout_secs: int) -> None:
        super().__init__(
            "task '{task_id}' is still running after {timeout_secs}s of waiting".format(
                task_id=task_id, timeout_secs=timeout_secs,
            ),
        )
        self.task_id = task_id
        self.timeout_secs = timeout_secs


class TaskResourceMissingError(Exception):
    def __init__(self, task_id: str, resource_type: str) -> None:
        super().__init__(
            "task '{task_id}' has no resource of type '{resource_type}'".format(
                task_id=task_id, resource_type=resource_type,
            ),
        )
        self.task_id = task_id
        self.resource_type = resource_type
