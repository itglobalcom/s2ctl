from ssclient.affinity_group import AffinityGroupService
from ssclient.domain.domain import DomainService
from ssclient.gateway.gateway import GatewayService
from ssclient.metainfo import ApplicationsService, ImagesService, LocationsService
from ssclient.network.network import NetworkService
from ssclient.ports import HttpClientPort
from ssclient.project import ProjectService
from ssclient.server.server import ServerService
from ssclient.sshkey import SshkeyService
from ssclient.task import TaskService
from ssclient.vmware.vmware import VmwareService


class SSClient(object):  # noqa: WPS214
    def __init__(self, http_client: HttpClientPort) -> None:
        self._http_client = http_client

    def locations(self) -> LocationsService:
        return LocationsService(self._http_client)

    def images(self) -> ImagesService:
        return ImagesService(self._http_client)

    def applications(self) -> ApplicationsService:
        return ApplicationsService(self._http_client)

    def project(self) -> ProjectService:
        return ProjectService(self._http_client)

    def servers(self) -> ServerService:
        return ServerService(self._http_client)

    def sshkeys(self) -> SshkeyService:
        return SshkeyService(self._http_client)

    def tasks(self) -> TaskService:
        return TaskService(self._http_client)

    def networks(self) -> NetworkService:
        return NetworkService(self._http_client)

    def domains(self) -> DomainService:
        return DomainService(self._http_client)

    def affinity_groups(self) -> AffinityGroupService:
        return AffinityGroupService(self._http_client)

    def gateways(self) -> GatewayService:
        return GatewayService(self._http_client)

    def vmware(self) -> VmwareService:
        return VmwareService(self._http_client)
