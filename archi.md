# `archi.md` — s2ctl

> Архитектурный контракт репозитория. Кратко: границы, ограничения, контракты.
> Межрепозиторные рёбра — только в `workspace.yaml` корня workspace.

## 1) Context ID / Owner / Repository mapping

| Context ID | Owner | Repository | Code paths |
| --- | --- | --- | --- |
| ctx_cli_s2ctl | team/backend | s2ctl | src/s2ctl, src/ssclient, tests, bundle, docker |

Репозиторий одноконтекстный: CLI и его клиентский слой — один контекст,
инфраструктура сборки бинаря (`bundle/`, `docker/`) принадлежит ему же.

## 2) Boundaries (in/out of scope)

- In scope: команды CLI и их справка (`src/s2ctl`), клиентский слой контракта
  `public-api` (`src/ssclient`), локальный конфиг и контексты (ключи проектов
  в keyring), ожидание асинхронных задач платформы, сборка единого бинаря
  для Linux и Windows.
- Out of scope: доменные правила и валидация услуг (владелец — `cloudmng`);
  остальные внешние API монолита (`partner-api`, `referral-api`, Admin API v3);
  генерация клиентского слоя из OpenAPI — слой рукописный; раздел Kubernetes
  контракта (выведен из объёма TSK0003840).
- Primary L1 context: `ctx_cli_s2ctl`; Affected L1 contexts: нет.

## 3) Layering constraints

- Слои: `ssclient` → `s2ctl`. `ssclient` — HTTP к `public-api`, пути, payload'ы
  и разбор ответа; `s2ctl` — разбор аргументов, вызов сервиса, вывод.
- Разрешено: `s2ctl.cmd_*` получает сервис фабрикой `ssclient.client`
  и печатает результат через `echo`/`FORMATTERS` из `s2ctl.click`.
- Запрещено: HTTP-вызов и разбор ответа в `cmd_*`; импорт `s2ctl` из `ssclient`
  (обратная зависимость слоёв); `print` и построчная сборка ответа в обработчике
  команды; группа команд без регистрации в `src/s2ctl/__init__.py` — в бинарь
  попадает только то, что импортировано оттуда.

## 4) External contracts (API/events)

| Contract | Type | Direction | Owner | Compatibility |
| --- | --- | --- | --- | --- |
| `public-api` — REST монолита | API | in | cloudmng | consumer: CLI следует за publisher'ом и своего контракта не определяет |
| поверхность CLI — имена команд, аргументов и форматы вывода | CLI | out | ctx_cli_s2ctl | имена и аргументы существующих команд не меняются: на них написаны пользовательские скрипты |

Локальный конфиг и keyring — не контракт: приватное состояние машины пользователя.

## 5) Quality gates and testing

- Tests: клиентский слой — `tests/ssclient/**` по образцу `test_http_client.py`
  (локальный `aiohttp`-сервер из `tests/conftest.py`: метод, путь, payload,
  разбор ответа) — Required; слой команд — `tests/s2ctl/**`, состав дерева
  команд и разбор аргументов — Required; тестов на форматтеры и help-тексты
  не создавать.
- Gates: `poetry install`; `make test` (pytest, покрытие `src`); `flake8 src`
  (wemake-python-styleguide, конфиг `.flake8`); `make pyright`
  (`pyright ./src`, конфиг `[tool.pyright]` в `pyproject.toml` — тот же гейт
  запускает шаблон CI); `make test-tox` (матрица py310, py312);
  `bash bundle/build_linux.sh` (единый бинарь).
- Done: гейты зелёные; новая группа команд зарегистрирована
  в `src/s2ctl/__init__.py`; у read-команды есть `--output`, у асинхронной —
  `--wait`; новое подавление в `.flake8` или `pyright` — с обоснованием.

## 6) Known legacy deviations

| Deviation | Impact/Risk | Mitigation plan |
| --- | --- | --- |
| `server power-off` и `server reboot` переключаются флагом `--hard` между парами операций API (`power/shutdown`↔`power/off`, `power/reboot`↔`power/reset`) — две команды на четыре операции | нарушение GR-01: флаг меняет смысл команды; на новые разделы не тиражируется (VMware-питание — 5 отдельных команд) | развести на отдельные команды отдельной карточкой: правка ломает поверхность CLI, поэтому в TSK0003840 не входит |
| Состав команд собирается импортами в `src/s2ctl/__init__.py` (подавления WPS412, WPS235) | забытый импорт = команда есть в коде, но отсутствует в бинаре, и обнаруживается только вручную | тест дерева команд `tests/s2ctl/test_cli_tree.py` — обязательное дополнение при каждой новой группе |
| `async-timeout` вместо `asyncio.timeout` в `ssclient.base` | лишняя зависимость ради Python 3.10 | убрать при подъёме минимальной версии Python до 3.11 |
| Типовой гейт `pyright` заведён в задаче TSK0003840 на легаси-коде: из 19 находок 15 устранены правками, 4 закрыты двумя обоснованными подавлениями (динамический `Literal` из enum в `ssclient/domain/record_entities.py`, сужение `Optional` в `s2ctl/cmd_sshkey.py`) | гейт зелёный, но два места типами не описаны | снять подавления вместе с переработкой типов записей DNS — отдельной карточкой |
| Образы сборки (`docker/Dockerfile.*`) и CI (`.gitlab-ci.yml` → внешний шаблон `b2c/ci`) не воспроизводятся локальными гейтами | расхождение локальной сборки и пайплайна ловится только запуском пайплайна в MR | держать `bundle/build_linux.sh` единственной точкой сборки, образ — только окружением для него |

## 7) Change policy and required reviews

- Policy: новая операция контракта = отдельная команда (GR-01), а не флаг-режим
  у существующей; имена и аргументы существующих команд не меняются;
  `pyproject.toml` и `poetry.lock` правятся парой.
- Required reviews: владелец контекста; интеграции — при добавлении раздела
  контракта `public-api` в CLI.
- Escalation triggers: изменение имени или аргумента существующей команды;
  обращение к API, отличному от `public-api`; HTTP-вызов в обход `ssclient`;
  расширение `per-file-ignores` в `.flake8` без обоснования.
