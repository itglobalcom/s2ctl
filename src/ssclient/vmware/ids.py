"""Идентификаторы раздела VMware.

У publisher'а это произвольные положительные целые — проверять в них нечего, фабрика
не нужна. Но в одной сигнатуре их встречается по два и по три (`nic_id` и `network_id`,
`server_id` и `image_id`, заказ сервера — сразу четыре), и `int` не мешает переставить
их местами. `NewType` ничего не стоит в рантайме и такую перестановку ловит типами.
"""
from typing import NewType

VmwareLocationId = NewType('VmwareLocationId', int)
VmwareImageId = NewType('VmwareImageId', int)
VmwareGpuModelId = NewType('VmwareGpuModelId', int)
VmwareNetworkId = NewType('VmwareNetworkId', int)
VmwareServerId = NewType('VmwareServerId', int)
VmwareNicId = NewType('VmwareNicId', int)
VmwareVolumeId = NewType('VmwareVolumeId', int)
VmwareNatRuleId = NewType('VmwareNatRuleId', int)
VmwareVpnTunnelId = NewType('VmwareVpnTunnelId', int)
