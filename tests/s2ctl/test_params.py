"""Разбор набора правил из файла: `--rules-file` принимает то, что печатает парная `get-*`."""
import io
import json

import click
import pytest

from s2ctl.params import parse_rules

RULE = {'name': 'ssh', 'action': 'Allow'}


def _parse(printed):
    return parse_rules(None, None, io.StringIO(json.dumps(printed)))


def test_array_of_rules_is_taken_as_is():
    assert _parse([RULE]) == [RULE]


def test_rule_set_object_of_the_edge_firewall_is_unwrapped():
    # Из четырёх парных `get-*` только `vmware edge get-firewall` печатает набор
    # правил внутри объекта — вместе с состоянием самого экрана.
    printed = {'enabled': True, 'default_action': 'Deny', 'rules': [RULE]}

    assert _parse(printed) == [RULE]


def test_object_without_a_rule_set_is_rejected():
    with pytest.raises(click.BadParameter):
        _parse({'enabled': True})


def test_empty_file_is_taken_as_an_empty_rule_set():
    # Парная `get-*` печатает набор без правил пустым выводом, поэтому файл,
    # снятый со шлюза без правил, пуст — и round-trip замыкается и на нём.
    assert parse_rules(None, None, io.StringIO('')) == []


def test_file_of_whitespace_is_taken_as_an_empty_rule_set():
    assert parse_rules(None, None, io.StringIO('\n')) == []


def test_file_that_is_not_json_is_rejected():
    with pytest.raises(click.BadParameter):
        parse_rules(None, None, io.StringIO('not json'))
