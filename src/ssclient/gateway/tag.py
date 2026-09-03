from typing import ClassVar, TypedDict
from urllib.parse import quote

from ssclient.base import BaseService
from ssclient.gateway.gateway_id import GatewayId
from ssclient.ports import HttpClientPort


class TagEntity(TypedDict):
    value: str  # noqa: WPS110


class TagService(BaseService):
    _path: ClassVar[str] = 'api/v1/gateways/{gateway_id}/tags'

    def __init__(self, http_client: HttpClientPort, gateway_id: GatewayId) -> None:
        super().__init__(http_client, {'gateway_id': gateway_id.value})

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
