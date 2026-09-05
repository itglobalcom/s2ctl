from typing import ClassVar, TypedDict
from urllib.parse import quote

from ssclient.base import BaseService
from ssclient.ports import HttpClientPort
from ssclient.server.server_id import ServerId


class TagEntity(TypedDict):
    value: str  # noqa: WPS110


class TagService(BaseService):
    _path: ClassVar[str] = 'api/v1/servers/{server_id}/tags'

    def __init__(self, http_client: HttpClientPort, server_id: ServerId) -> None:
        super().__init__(http_client, {'server_id': server_id.value})

    async def create(self, *, name: str) -> TagEntity:
        return await self._http_client.post(
            path=self.path,
            payload={
                'value': name,
            },
        )

    async def delete(self, name: str) -> None:
        # Publisher берёт тег из последнего сегмента пути и декодирует его сам,
        # поэтому разделители внутри имени должны уехать percent-encoded.
        path = self._make_path(quote(name, safe=''))
        await self._http_client.delete(path)
