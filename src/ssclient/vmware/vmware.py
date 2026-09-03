from ssclient.ports import HttpClientPort
from ssclient.vmware.metainfo import (
    VmwareGpuModelsService,
    VmwareImagesService,
    VmwareLocationsService,
)
from ssclient.vmware.network import VmwareNetworkService


class VmwareService(object):
    """Разделы услуги VMware: каталог и сети со шлюзом edge."""

    def __init__(self, http_client: HttpClientPort) -> None:
        self._http_client = http_client

    def locations(self) -> VmwareLocationsService:
        return VmwareLocationsService(self._http_client)

    def images(self) -> VmwareImagesService:
        return VmwareImagesService(self._http_client)

    def gpu_models(self) -> VmwareGpuModelsService:
        return VmwareGpuModelsService(self._http_client)

    def networks(self) -> VmwareNetworkService:
        return VmwareNetworkService(self._http_client)
