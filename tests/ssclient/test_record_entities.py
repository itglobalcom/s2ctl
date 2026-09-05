"""Реестр типов записей DNS: состав полей записи берётся из её сущности."""
import pytest

from ssclient.domain import record_entities as entities


@pytest.mark.parametrize('record_type', tuple(entities.AllowedRecordType))
def test_every_record_type_declares_its_own_fields(record_type):
    record_fields = entities.record_type_fields(record_type)

    # Тип записи без сущности уронил бы команду в рантайме: реестр обязан быть полным.
    assert record_fields
    assert not record_fields & entities.BASE_RECORD_FIELDS


def test_record_type_values_are_the_choices_of_the_command():
    assert entities.AllowedRecordType.list() == [
        record_type.value for record_type in entities.AllowedRecordType
    ]
