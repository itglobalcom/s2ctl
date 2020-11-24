from typing import List, TypedDict

from ssclient.base import BaseService


class LocationEntity(TypedDict):
    id: str  # noqa: WPS125
    system_volume_min: int
    additional_volume_min: int
    volume_max: int
    windows_system_volume_min: int
    bandwidth_min: int
    bandwidth_max: int
    cpu_quantity_options: List[int]
    ram_size_options: List[int]


class ImageEntity(TypedDict):
    id: str  # noqa: WPS125
    location_id: str
    type: str  # noqa: WPS125
    os_version: str
    architecture: str
    allow_ssh_keys: bool


class LocationsService(BaseService):
    _path = 'api/v1/locations'

    async def get(self) -> List[LocationEntity]:
        locations_resp = await self._http_client.get(self.path)
        return locations_resp['locations']


class ImagesService(BaseService):
    _path = 'api/v1/images'

    async def get(self) -> List[ImageEntity]:
        images_resp = await self._http_client.get(self.path)
        return images_resp['images']
