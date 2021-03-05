from typing import ClassVar, TypedDict

from ssclient.base import BaseService
from ssclient.ports import HttpClientPort


class TagEntity(TypedDict):
    value: str  # noqa: WPS110


class TagService(BaseService):
    _path: ClassVar[str] = 'api/v1/servers/{server_id}/tags'

    def __init__(self, http_client: HttpClientPort, server_id: str) -> None:
        super().__init__(http_client, {'server_id': server_id})

    async def create(self, *, name: str) -> TagEntity:
        return await self._http_client.post(
            path=self.path,
            payload={
                'value': name,
            },
        )

    async def delete(self, name: str) -> None:
        path = self._make_path(name)
        await self._http_client.delete(path)
