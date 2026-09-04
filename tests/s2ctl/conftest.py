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

# Ключ-заглушка вызова CLI: без ключа команда останавливается до сервиса. Значение
# ни один тест не проверяет, но префикс `02` обязан быть известен `HOSTS_MAP` —
# иначе адрес API не выбирается и команда отказывает раньше проверяемого.
APIKEY = '02dadsd'

# Модули, чьи команды покрыты здесь: каждая команда берёт сервис фабрикой клиента,
# и подменяется именно она — доменные сервисы остаются настоящими. Командам подгрупп
# (`vmware server`, `vmware edge`) сервис отдаёт `cmd_vmware`, своей подмены им не нужно.
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
