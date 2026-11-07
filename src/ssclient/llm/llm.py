from ssclient.llm.access_key import LlmAccessKeyService
from ssclient.llm.connection import LlmConnectionService
from ssclient.llm.group import LlmGroupService
from ssclient.llm.model import LlmModelService
from ssclient.llm.package import LlmPackageService
from ssclient.llm.usage import LlmUsageService
from ssclient.ports import HttpClientPort


class LlmService(object):
    """Разделы услуги LLM: подключение, группы, ключи, каталог моделей, пакет и расход."""

    def __init__(self, http_client: HttpClientPort) -> None:
        self._http_client = http_client

    def connection(self) -> LlmConnectionService:
        return LlmConnectionService(self._http_client)

    def groups(self) -> LlmGroupService:
        return LlmGroupService(self._http_client)

    def access_keys(self) -> LlmAccessKeyService:
        return LlmAccessKeyService(self._http_client)

    def models(self) -> LlmModelService:
        return LlmModelService(self._http_client)

    def package(self) -> LlmPackageService:
        return LlmPackageService(self._http_client)

    def usage(self) -> LlmUsageService:
        return LlmUsageService(self._http_client)
