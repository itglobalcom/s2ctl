import ssl
from typing import Any, Dict, Optional
from urllib import parse as urlparse

import certifi
from aiohttp import ClientResponse, ClientResponseError, ClientSession, hdrs

from ssclient import errors


def _error_message(body: Any, reason: str) -> Any:
    """Причина отказа: `errors` из тела ответа контракта, иначе само тело, иначе статус."""
    if isinstance(body, dict):
        body = body.get('errors') or body
    return body or reason


class HttpClient(object):  # noqa: WPS214
    def __init__(self, host: str, apikey: Optional[str]) -> None:
        self.host = host
        self.apikey = apikey
        self.user_agent = 's2ctl'
        self._sslcontext = ssl.create_default_context(cafile=certifi.where())

    async def make_request(
        self, method: str, path: str, payload: Any = None,
    ) -> Any:
        async with ClientSession(connector_owner=True) as sess:
            request_manager = sess.request(
                method=method,
                url=urlparse.urljoin(self.host, path),
                headers=self.headers,
                json=payload,
                ssl=self._sslcontext,
            )
            async with request_manager as resp:
                return await self._process_response(resp)

    async def get(self, path: str) -> Any:
        return await self.make_request(hdrs.METH_GET, path)

    async def post(self, path: str, payload: Any) -> Any:
        return await self.make_request(hdrs.METH_POST, path, payload)

    async def put(self, path: str, payload: Any) -> Any:
        return await self.make_request(hdrs.METH_PUT, path, payload)

    async def patch(self, path: str, payload: Any) -> Any:
        return await self.make_request(hdrs.METH_PATCH, path, payload)

    async def delete(self, path: str) -> Any:
        return await self.make_request(hdrs.METH_DELETE, path)

    @property
    def headers(self) -> Dict[str, str]:
        headers = {
            'User-Agent': self.user_agent,
        }
        if self.apikey:
            headers.update({'X-API-KEY': self.apikey})

        return headers

    async def _process_response(self, resp: ClientResponse) -> Any:
        msg = await self._read_body(resp)
        try:
            resp.raise_for_status()
        except ClientResponseError as exc:
            raise errors.HttpClientResponseError(exc.status, _error_message(msg, exc.message))
        return msg

    async def _read_body(self, resp: ClientResponse) -> Any:
        try:
            return await resp.json(content_type=None)
        except ValueError:
            # Отказ приходит и не в JSON контракта — страницей прокси, простым текстом:
            # такое тело всё равно годится в сообщение об ошибке.
            return await resp.text()
