from typing import TypedDict

from ssclient.base import BaseService


class ProjectEntity(TypedDict):
    id: str  # noqa: WPS125
    balance: float
    currency: str
    state: str
    created: str


class ProjectService(BaseService):
    path = 'api/v1/project'

    async def get(self) -> ProjectEntity:
        project_resp = await self._http_client.get(self.path)
        return project_resp['project']
