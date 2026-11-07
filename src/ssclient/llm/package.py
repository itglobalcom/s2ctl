from typing import ClassVar, List

from ssclient.base import BaseService
from ssclient.llm.entities import LlmCurrentPackageEntity, LlmPackagePlanEntity


class LlmPackageService(BaseService):
    _path: ClassVar[str] = 'api/v1/llm/'

    async def get(self) -> LlmCurrentPackageEntity:
        package_resp = await self._http_client.get(self._make_path('package'))
        return package_resp['package']

    async def plans(self) -> List[LlmPackagePlanEntity]:
        plans_resp = await self._http_client.get(self._make_path('package-plans'))
        return plans_resp['package_plans']
