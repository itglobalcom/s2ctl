from dataclasses import dataclass, field
from typing import List, Optional, Sequence, TypedDict

from ssclient.vmware.ids import (
    VmwareGpuModelId,
    VmwareImageId,
    VmwareLocationId,
    VmwareNetworkId,
)


class VmwareServerGpuEntity(TypedDict):
    model_id: int
    vram_mb: int
    card_count: int


class VmwareServerNicEntity(TypedDict):
    id: int  # noqa: WPS125
    number: int
    is_primary: bool
    network_id: int
    ip: str
    mac: str
    bandwidth_mbps: int


class VmwareServerEntity(TypedDict):
    id: int  # noqa: WPS125
    project_id: int
    location_id: int
    name: str
    computer_name: str
    state: str
    cpu: int
    ram_mb: int
    system_disk_mb: int
    system_disk_type: str
    image_id: int
    is_power_on: bool
    # Живое поле: publisher заполняет его только в ответе чтения одного сервера,
    # в списке серверов оно отсутствует.
    vm_tools_installed: bool
    nested_hypervisor: bool
    gpu: VmwareServerGpuEntity
    nics: List[VmwareServerNicEntity]
    created: str


class VmwareServerOrderRef(TypedDict):
    """Ответ на заказ сервера: id созданного сервера рядом с id его задачи."""

    server_id: int
    task_id: str


@dataclass(frozen=True)
class VmwareServerGpu(object):
    """Профиль GPU заказываемого сервера: platform выбирает нарезку по всей тройке сразу."""

    gpu_model_id: VmwareGpuModelId
    vram_mb: int
    card_count: int


@dataclass(frozen=True)
class VmwareServerOrder(object):  # noqa: WPS230
    """Заказ VMware-сервера — одно тело запроса и на создание, и на его предпроверку."""

    location_id: VmwareLocationId
    name: str
    image_id: VmwareImageId
    cpu_count: int
    ram_mb: int
    system_disk_size_mb: int
    computer_name: Optional[str] = None
    system_disk_type: Optional[str] = None
    public_network_id: Optional[VmwareNetworkId] = None
    network_bandwidth_mbps: Optional[int] = None
    backup_enabled: bool = False
    backup_period: Optional[int] = None
    # Своего типа идентификатора SSH-ключа в репозитории нет: он заводится вместе
    # с типизацией группы команд `ssh-key`.
    ssh_keys: Sequence[int] = field(default_factory=tuple)
    need_sysprep: bool = False
    nested_hypervisor: bool = False
    gpu: Optional[VmwareServerGpu] = None
