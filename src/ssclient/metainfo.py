from typing import List, Optional, TypedDict

from ssclient.base import BaseService, with_filters


class LocationEntity(TypedDict):
    id: str
    system_volume_min: int
    additional_volume_min: int
    volume_max: int
    windows_system_volume_min: int
    bandwidth_min: int
    bandwidth_max: int
    cpu_quantity_options: List[int]
    ram_size_options: List[int]


class ImageEntity(TypedDict):
    id: str
    location_id: str
    type: str
    os_version: str
    architecture: str
    allow_ssh_keys: bool


class ApplicationEntity(TypedDict):
    id: str
    location_id: str
    images: List[str]


class LocationsService(BaseService):
    _path = 'api/v1/locations'

    async def get(self) -> List[LocationEntity]:
        locations_resp = await self._http_client.get(self.path)
        return locations_resp['locations']


class ImagesService(BaseService):
    _path = 'api/v1/images'

    async def get(self, location_id: Optional[str] = None) -> List[ImageEntity]:
        path = with_filters(self.path, {'location_id': location_id})
        images_resp = await self._http_client.get(path)
        return images_resp['images']


class ApplicationsService(BaseService):
    _path = 'api/v1/applications'

    async def get(
        self,
        location_id: Optional[str] = None,
        application_id: Optional[str] = None,
        image_id: Optional[str] = None,
    ) -> List[ApplicationEntity]:
        path = with_filters(self.path, {
            'location_id': location_id,
            'application_id': application_id,
            'image_id': image_id,
        })
        applications_resp = await self._http_client.get(path)
        return applications_resp['applications']
