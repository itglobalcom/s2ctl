import ssl
from typing import Any, Dict, Optional
from urllib import parse as urlparse

import aiohttp
import certifi
from aiohttp import client_exceptions, hdrs

from ssclient import errors


class HttpClient(object):  # noqa: WPS214
    def __init__(self, host: str, apikey: Optional[str]) -> None:
        self.host = host
        self.apikey = apikey
        self._sslcontext = ssl.create_default_context(cafile=certifi.where())

    async def make_request(
        self, method: str, path: str, payload: Any = None,
    ) -> Any:
        async with aiohttp.ClientSession(connector_owner=True) as sess:
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
        if self.apikey:
            return {'X-API-KEY': self.apikey}
        return {}

    async def _process_response(self, resp: aiohttp.ClientResponse) -> Any:
        msg = await resp.json(content_type=None)
        try:
            resp.raise_for_status()
        except client_exceptions.ClientResponseError as exc:
            if isinstance(msg, dict):
                err_message = msg.get('errors')
            else:
                err_message = msg or exc.message  # noqa: B306
            raise errors.HttpClientResponseError(exc.status, err_message)  # noqa: B306
        return msg
