from typing import ClassVar, Dict, Iterable, List, Optional, TypedDict

from ssclient.base import BaseService

NetworksPayload = List[Dict[str, int]]


class ServerPriceEntity(TypedDict):
    price: float


def _networks_payload(networks: Iterable[int]) -> Optional[NetworksPayload]:
    """Отсутствие сетей и пустой список для publisher'а разные.

    На `null` он считает цену с одним публичным интерфейсом минимальной ширины,
    на пустой список — цену конфигурации вовсе без сети.
    """
    bandwidths = [{'bandwidth_mbps': bandwidth} for bandwidth in networks]
    return bandwidths or None


class ServerPriceService(BaseService):
    _path: ClassVar[str] = 'api/v1/servers/price'

    async def calculate(
        self,
        *,
        location_id: str,
        image_id: str,
        cpu: int,
        ram_mb: int,
        volumes: Iterable[int],
        networks: Iterable[int] = (),
    ) -> ServerPriceEntity:
        return await self._http_client.post(
            path=self.path,
            payload={
                'location_id': location_id,
                'image_id': image_id,
                'cpu': cpu,
                'ram_mb': ram_mb,
                'volumes': [{'size_mb': size_mb} for size_mb in volumes],
                'networks': _networks_payload(networks),
            },
        )
