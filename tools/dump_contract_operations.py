"""Снимок операций контракта `public-api` из исходников publisher'а.

Запуск:

    python tools/dump_contract_operations.py <путь к рабочей копии cloudmng> \
        > tests/s2ctl/contract_operations.txt

Разбирает `[Route]` контроллеров и `[Http*]` их действий в
`Com.Cloudmng.Api.Public/Controllers/**`. Путь, заданный ссылкой на
`const string`, раскрывается по объявлению константы: нераскрытая ссылка —
это молча потерянная операция, поэтому она роняет разбор, а не пропускается.
"""
import argparse
import pathlib
import re
# S404: ревизию publisher'а даёт только его git — инструмент сопровождения зовёт
# его локально, в бинарь CLI этот модуль не входит.
import subprocess  # noqa: S404
import sys
from typing import Dict, Iterator, List, Optional, Tuple

PROJECT_DIR = 'Com.Cloudmng.Api.Public'
CONTROLLERS_DIR = 'Controllers'

HTTP_VERBS = {
    'HttpGet': 'GET',
    'HttpPost': 'POST',
    'HttpPut': 'PUT',
    'HttpPatch': 'PATCH',
    'HttpDelete': 'DELETE',
    'HttpHead': 'HEAD',
    'HttpOptions': 'OPTIONS',
}

_ATTRIBUTE_LINE = re.compile(r'^\[(?P<body>.+)\]$')
_CLASS_LINE = re.compile(r'\bclass\s+(?P<name>\w+)\s*(?::\s*(?P<base>[\w.<>]+))?')
_ACTION_LINE = re.compile(r'\bpublic\s+(?:async\s+)?[\w<>\[\],.\s]+?\s(?P<name>\w+)\s*\(')
_CONST_LINE = re.compile(r'const\s+string\s+(?P<name>\w+)\s*=\s*"(?P<value>[^"]*)"')
_ARGUMENT = r'"(?:[^"\\]|\\.)*"|[A-Za-z_][\w.]*'
_ROUTE_ATTRIBUTE = re.compile(r'^Route\s*\(\s*(?P<argument>' + _ARGUMENT + r')\s*\)$')
_HTTP_ATTRIBUTE = re.compile(
    r'(?P<verb>Http\w+)\s*(?:\(\s*(?P<argument>' + _ARGUMENT + r')\s*\))?',
)
# Ограничение маршрутизации ASP.NET: имя параметра от нас отделяет ':', дальше
# либо `regex(...)` с одним уровнем вложенных скобок, либо ограничение с
# необязательными аргументами.
_CONSTRAINT = re.compile(r':(?:regex\((?:[^()]|\([^()]*\))*\)|\w+(?:\([^()]*\))?)')


def _strip_comment(line: str) -> str:
    quoted = False
    for position, symbol in enumerate(line):
        if symbol == '"':
            quoted = not quoted
        elif symbol == '/' and not quoted and line[position:position + 2] == '//':
            return line[:position].strip()
    return line


class UnresolvedRouteLiteral(Exception):
    """Путь маршрута задан выражением, которое разбор не раскрывает."""


class AmbiguousOperation(Exception):
    """Разные маршруты publisher'а дали одну строку снимка."""


def _iter_sources(directory: pathlib.Path) -> Iterator[pathlib.Path]:
    return iter(sorted(directory.rglob('*.cs')))


def _read(source: pathlib.Path) -> List[str]:
    return source.read_text(encoding='utf-8-sig').splitlines()


def _collect_constants(project: pathlib.Path) -> Dict[str, str]:
    constants: Dict[str, str] = {}
    for source in _iter_sources(project):
        holder = ''
        for line in _read(source):
            declaration = _CLASS_LINE.search(line)
            if declaration:
                holder = declaration.group('name')
            constant = _CONST_LINE.search(line)
            if constant:
                constants[constant.group('name')] = constant.group('value')
                constants['{0}.{1}'.format(holder, constant.group('name'))] = constant.group('value')
    return constants


def _literal(argument: str, constants: Dict[str, str]) -> str:
    argument = argument.strip()
    if argument.startswith('"'):
        return argument[1:-1].replace('\\\\', '\\')
    for name in (argument, argument.rsplit('.', 1)[-1]):
        if name in constants:
            return constants[name]
    raise UnresolvedRouteLiteral(argument)


def _class_route(attributes: List[str], constants: Dict[str, str]) -> Optional[str]:
    for attribute in attributes:
        route = _ROUTE_ATTRIBUTE.match(attribute.strip())
        if route:
            return _literal(route.group('argument'), constants)
    return None


def _action_verbs(
    attributes: List[str], constants: Dict[str, str],
) -> List[Tuple[str, str]]:
    verbs: List[Tuple[str, str]] = []
    for attribute in attributes:
        for match in _HTTP_ATTRIBUTE.finditer(attribute):
            verb = HTTP_VERBS.get(match.group('verb'))
            if verb is None:
                continue
            argument = match.group('argument')
            verbs.append((verb, _literal(argument, constants) if argument else ''))
    return verbs


def _join(class_route: str, action_route: str) -> str:
    if action_route.startswith(('/', '~/')):
        return action_route.lstrip('~').lstrip('/')
    return '/'.join(part for part in (class_route, action_route) if part)


def _normalize(route: str) -> str:
    return '/{0}'.format(_CONSTRAINT.sub('', route).strip('/'))


def _operations_of_source(  # noqa: WPS210, WPS231
    source: pathlib.Path,
    constants: Dict[str, str],
    class_routes: Dict[str, str],
) -> Iterator[Tuple[str, str]]:
    attributes: List[str] = []
    current_route = ''
    for line in _read(source):
        stripped = _strip_comment(line.strip())
        attribute = _ATTRIBUTE_LINE.match(stripped)
        if attribute:
            attributes.append(attribute.group('body'))
            continue
        declaration = _CLASS_LINE.search(stripped)
        if declaration:
            route = _class_route(attributes, constants)
            if route is None:
                route = class_routes.get(declaration.group('base') or '', '')
            class_routes[declaration.group('name')] = route
            current_route = route
            attributes = []
            continue
        action = _ACTION_LINE.search(stripped)
        if action and attributes:
            for verb, action_route in _action_verbs(attributes, constants):
                route = _join(current_route, action_route)
                yield (
                    '{0} {1}'.format(verb, _normalize(route)),
                    '{0} {1}'.format(verb, route),
                )
        if stripped:
            attributes = []


def dump_operations(publisher: pathlib.Path) -> List[str]:
    """Операции контракта publisher'а: строки «метод путь», без повторов."""
    project = publisher / PROJECT_DIR
    constants = _collect_constants(project)
    class_routes: Dict[str, str] = {}
    operations: Dict[str, set] = {}
    for source in _iter_sources(project / CONTROLLERS_DIR):
        for operation, route in _operations_of_source(source, constants, class_routes):
            operations.setdefault(operation, set()).add(route)
    ambiguous = {key: sorted(routes) for key, routes in operations.items() if len(routes) > 1}
    if ambiguous:
        # Снятое ограничение маршрутизации склеило разные маршруты в одну операцию:
        # счёт занижен, и таблица покрытия сравнялась бы с неполным снимком.
        raise AmbiguousOperation(ambiguous)
    return sorted(operations)


def _revision(publisher: pathlib.Path) -> str:
    # S603: команда собрана здесь списком, без оболочки, и снаружи в неё приходит
    # только путь к рабочей копии. S607: git берётся из PATH — своего пути к нему
    # у рабочей копии разработчика нет.
    revision = subprocess.run(  # noqa: S603
        ['git', '-C', str(publisher), 'rev-parse', 'HEAD'],  # noqa: S607
        capture_output=True,
        check=True,
        text=True,
    )
    return revision.stdout.strip()


def main() -> None:
    """Печатает снимок в stdout."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('publisher', type=pathlib.Path, help='рабочая копия cloudmng')
    parser.add_argument('--revision', default=None, help='ревизия publisher для заголовка')
    parsed = parser.parse_args()
    revision = parsed.revision or _revision(parsed.publisher)
    operations = dump_operations(parsed.publisher)
    sys.stdout.write('# Снимок операций контракта public-api: метод и путь маршрута.\n')
    sys.stdout.write('# publisher: cloudmng @ {0}\n'.format(revision))
    sys.stdout.write('# снят: python tools/dump_contract_operations.py <cloudmng>\n')
    sys.stdout.write('# Ограничения маршрутизации (:int, :regex(...)) сняты.\n')
    sys.stdout.write('{0}\n'.format('\n'.join(operations)))


if __name__ == '__main__':
    main()
