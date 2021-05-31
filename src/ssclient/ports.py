from abc import abstractmethod
from typing import Any, Optional, Protocol


class HttpClientPort(Protocol):
    def __init__(self, host: str, api_key: Optional[str]) -> None:
        ...

    @abstractmethod
    async def get(self, path: str) -> Any:
        ...

    @abstractmethod
    async def post(self, path: str, payload: Any) -> Any:
        ...

    @abstractmethod
    async def put(self, path: str, payload: Any) -> Any:
        ...

    @abstractmethod
    async def patch(self, path: str, payload: Any) -> Any:
        ...

    @abstractmethod
    async def delete(self, path: str) -> Any:
        ...
