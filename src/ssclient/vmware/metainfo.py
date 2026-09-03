from typing import ClassVar, List, Optional, TypedDict

from ssclient.base import BaseService, with_filters
from ssclient.vmware.ids import VmwareLocationId


class VmwareLocationDiskTypeEntity(TypedDict):
    title: str
    is_default: bool
    is_ssd: bool
    is_allowed_for_system_disk: bool
    min_mb: int
    max_mb: int
    step_mb: int
    default_size_mb: int


class VmwareLocationEntity(TypedDict):
    id: int  # noqa: WPS125
    tech_title: str
    gpu_supported: bool
    nested_hypervisor_supported: bool
    disk_types: List[VmwareLocationDiskTypeEntity]


class VmwareImageEntity(TypedDict):
    id: int  # noqa: WPS125
    name: str
    os_family: str
    os_type: str
    min_ram_mb: int
    hdd_gb: int
    ssh_key_supported: bool
    cpu_hot_add: bool
    memory_hot_add: bool
    nic_hot_remove: bool
    is_gpu_only: bool
    supported_gpu_model_ids: List[int]


class VmwareGpuModelEntity(TypedDict):
    id: int  # noqa: WPS125
    tech_title: str
    name: str
    capacity_vram_mb: int
    gpu_card_count: int
    server_allocation_limit: int
    max_server_ram_mb: int
    is_available: bool


class VmwareLocationsService(BaseService):
    _path: ClassVar[str] = 'api/v1/vmware/locations'

    async def list(self) -> List[VmwareLocationEntity]:  # noqa: WPS125
        locations_resp = await self._http_client.get(self.path)
        return locations_resp['locations']


class VmwareImagesService(BaseService):
    _path: ClassVar[str] = 'api/v1/vmware/images'

    async def list(  # noqa: WPS125
        self, location_id: Optional[VmwareLocationId] = None, gpu: Optional[str] = None,
    ) -> List[VmwareImageEntity]:
        path = with_filters(self.path, {'location_id': location_id, 'gpu': gpu})
        images_resp = await self._http_client.get(path)
        return images_resp['images']


class VmwareGpuModelsService(BaseService):
    _path: ClassVar[str] = 'api/v1/vmware/gpu-models'

    async def list(  # noqa: WPS125
        self, location_id: Optional[VmwareLocationId] = None,
    ) -> List[VmwareGpuModelEntity]:
        path = with_filters(self.path, {'location_id': location_id})
        gpu_models_resp = await self._http_client.get(path)
        return gpu_models_resp['gpu_models']
