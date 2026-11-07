from typing import ClassVar

from ssclient.base import BaseService
from ssclient.llm.entities import LlmModelCatalogEntity, LlmModelDetailsEntity
from ssclient.llm.ids import LlmModelId


class LlmModelService(BaseService):
    _path: ClassVar[str] = 'api/v1/llm/models'

    async def list(self) -> LlmModelCatalogEntity:
        return await self._http_client.get(self.path)

    async def get(self, model_id: LlmModelId) -> LlmModelDetailsEntity:
        model_resp = await self._http_client.get(self._make_path(str(model_id)))
        return model_resp['model']
