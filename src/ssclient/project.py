from typing import ClassVar, TypedDict

from ssclient.base import BaseService


class ProjectEntity(TypedDict):
    id: str
    balance: float
    currency: str
    state: str
    created: str


class ProjectService(BaseService):
    _path: ClassVar[str] = 'api/v1/project'

    async def get(self) -> ProjectEntity:
        project_resp = await self._http_client.get(self.path)
        return project_resp['project']
