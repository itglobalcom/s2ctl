"""Идентификаторы раздела LLM: положительные целые publisher'а, обёрнутые от перестановки."""
from typing import NewType

LlmGroupId = NewType('LlmGroupId', int)
LlmAccessKeyId = NewType('LlmAccessKeyId', int)
LlmModelId = NewType('LlmModelId', int)
