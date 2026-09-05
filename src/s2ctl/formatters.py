import json
from typing import Any, Callable, Dict, Iterable, List, Optional, Protocol

import yaml
from tabulate import tabulate

INNER_FIELDS_ORDER = ('id', 'name')

# Скаляры JSON: их yaml печатает своим типом, как и json, — число числом,
# булево булевым, `null` пустотой. Всё остальное yaml пометил бы тегом
# `!!python/...`, поэтому такое значение печатается строкой.
_JSON_SCALAR_TYPES = (str, int, float, bool)

SorterType = Callable[[Any], Any]
AnyDict = Dict[Any, Any]


class FormatterPort(Protocol):
    def format(self, raw_obj: Any, sorter: Optional[SorterType] = None) -> str:
        """Prepare python objects and convert them to string before output.

        Args:
            raw_obj(Any): raw python object like dict, list or str.
            sorter(Optional[SorterType]): function for sorting fields order of raw_obj.
        """
        ...


def general_fields_sort(
    field_data: Any,
    fields_order: Iterable[str] = INNER_FIELDS_ORDER,
    _toplevel: bool = True,
) -> Any:
    if isinstance(field_data, list):
        return [general_fields_sort(data_item, fields_order, _toplevel) for data_item in field_data]

    if isinstance(field_data, dict):
        tail = field_data.copy()
        head = {}
        if not _toplevel:
            fields_order = INNER_FIELDS_ORDER

        for field_name in fields_order:
            if field_name in tail:
                head[field_name] = general_fields_sort(tail.pop(field_name), _toplevel=False)
        return {**head, **tail}

    return field_data


class JSONFormatter(object):
    def format(
        self,
        raw_obj: Any,
        sorter: Optional[SorterType] = None,
    ) -> str:
        if sorter:
            raw_obj = sorter(raw_obj)
        return json.dumps(raw_obj, indent=4, sort_keys=False)


class YAMLFormatter(object):
    def format(
        self,
        raw_obj: Any,
        sorter: Optional[SorterType] = None,
    ) -> str:
        if sorter:
            raw_obj = sorter(raw_obj)
        prep_obj = self._prepare_obj(raw_obj)
        return yaml.dump(prep_obj, sort_keys=False)

    def _prepare_obj(self, raw_obj: Any) -> Any:
        if not isinstance(raw_obj, (dict, List)):
            return self._prepare_scalar(raw_obj)

        if isinstance(raw_obj, list):
            if self._is_list_has_only_dicts(raw_obj):
                return {
                    list_item.get('id'): self._prepare_obj(list_item)
                    for list_item in raw_obj
                }
        elif isinstance(raw_obj, dict):
            prepared_dict = {}
            for key, value in raw_obj.items():  # noqa: WPS110
                prepared_dict[key] = self._prepare_obj(value)
            return prepared_dict

        return raw_obj

    def _prepare_scalar(self, raw_scalar: Any) -> Any:
        if raw_scalar is None or isinstance(raw_scalar, _JSON_SCALAR_TYPES):
            return raw_scalar
        return str(raw_scalar)

    def _is_list_has_only_dicts(self, raw_obj: List[Any]) -> bool:
        for list_item in raw_obj:
            if not isinstance(list_item, dict):
                return False
            if 'id' not in list_item:
                return False
        return True


class TableFormatter(object):
    def __init__(self, table_format: str = 'presto') -> None:
        self.table_foramt = table_format

    def format(
        self,
        raw_obj: Any,
        sorter: Optional[SorterType] = None,
    ) -> str:
        if sorter:
            raw_obj = sorter(raw_obj)
        if not isinstance(raw_obj, (dict, List)):
            return str(raw_obj)

        if isinstance(raw_obj, dict):
            raw_obj = [raw_obj]

        if not self._is_list_has_only_dicts(raw_obj):
            raw_obj = [{'value': list_item} for list_item in raw_obj]

        return tabulate(raw_obj, headers='keys', tablefmt=self.table_foramt)

    def _is_list_has_only_dicts(self, raw_obj: List[Any]) -> bool:
        for list_item in raw_obj:
            if isinstance(list_item, dict):
                return True
        return False
