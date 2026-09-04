"""Заглушка HTTP для тестов слоя команд.

Тесты этого каталога проверяют связку «опция CLI → поле запроса контракта»: команда
вызывается через `CliRunner`, снимается фактический запрос, и его тело сверяется
с формой запроса publisher'а. Правильность маршрута и разбора ответа проверена
на клиентском слое (`tests/ssclient/**`) и здесь не дублируется.
"""
import json
from typing import Any, Callable, Sequence

import pytest

from s2ctl import (
    cmd_affinity_group,
    cmd_domain,
    cmd_gateway,
    cmd_metainfo,
    cmd_server,
    cmd_vmware,
)
from ssclient.client import SSClient

# Группы, чьи команды покрыты здесь: каждая строит сервис фабрикой клиента, и подменяется
# именно она — доменные сервисы остаются настоящими. Подгруппы (`vmware server`,
# `vmware edge`) берут сервис у своей группы, отдельной подмены им не нужно.
_COMMAND_MODULES = (
    cmd_affinity_group,
    cmd_domain,
    cmd_gateway,
    cmd_metainfo,
    cmd_server,
    cmd_vmware,
)


@pytest.fixture
def cli_http_client(monkeypatch, fake_http_client):
    for command_module in _COMMAND_MODULES:
        monkeypatch.setattr(
            command_module, 'client_factory', lambda _ctx: SSClient(fake_http_client),
        )
    return fake_http_client


@pytest.fixture
def rules_file(tmp_path) -> Callable[[Sequence[Any]], str]:
    """Файл набора правил для команд, заменяющих набор целиком (`--rules-file`)."""
    def factory(rules: Sequence[Any]) -> str:
        path = tmp_path / 'rules.json'
        path.write_text(json.dumps(list(rules)))
        return str(path)

    return factory
