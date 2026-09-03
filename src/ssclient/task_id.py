import re
from typing import NamedTuple, Optional, Tuple

from ssclient import errors


class TaskIdFormat(NamedTuple):
    """Формат id задачи одной услуги: так услуга адресует задачу в маршруте её чтения."""

    service: str
    template: str
    pattern: re.Pattern
    is_always_completed: bool = False


VSTACK_TASK_ID = TaskIdFormat('vstack', 'l<location>t<id>', re.compile(r'^l\d*t\d+$'))
DNS_TASK_ID = TaskIdFormat('dns', 'dns<id>', re.compile(r'^dns\d+$'))
VMWARE_TASK_ID = TaskIdFormat('vmware', 'vmw<id>', re.compile(r'^vmw\d+$'))
# Синтетическая задача: её id отдают синхронные операции удаления (affinity-группы, теги),
# где реальной задачи не создаётся, а клиент опрашивает задачу так же, как в асинхронном случае.
ALREADY_COMPLETED_TASK_ID = TaskIdFormat(
    'vstack',
    'already_completed_task',
    re.compile(r'^already_completed_task$'),
    is_always_completed=True,
)

# Реестр форматов: услуга добавляется одной записью, остальной код о префиксах не знает.
TASK_ID_FORMATS: Tuple[TaskIdFormat, ...] = (
    VSTACK_TASK_ID,
    DNS_TASK_ID,
    VMWARE_TASK_ID,
    ALREADY_COMPLETED_TASK_ID,
)


def supported_formats_hint() -> str:
    return ', '.join(
        '{template} ({service})'.format(template=id_format.template, service=id_format.service)
        for id_format in TASK_ID_FORMATS
    )


class TaskId(NamedTuple):
    """Id задачи, разобранный по реестру форматов."""

    value: str  # noqa: WPS110
    id_format: TaskIdFormat

    @classmethod
    def try_parse(cls, raw_id: str) -> Optional['TaskId']:
        for id_format in TASK_ID_FORMATS:
            if id_format.pattern.match(raw_id):
                return cls(raw_id, id_format)
        return None

    @classmethod
    def parse(cls, raw_id: str) -> 'TaskId':
        task_id = cls.try_parse(raw_id)
        if task_id is None:
            raise errors.UnknownTaskIdError(raw_id, supported_formats_hint())
        return task_id

    @property
    def is_always_completed(self) -> bool:
        return self.id_format.is_always_completed
