from typing import List, TypedDict


class VmwareEdgeFirewallRuleEntity(TypedDict):
    enabled: bool
    name: str
    description: str
    action: str
    protocol: str
    source: str
    source_port: str
    destination: str
    destination_port: str


class VmwareEdgeFirewallEntity(TypedDict):
    enabled: bool
    default_action: str
    rules: List[VmwareEdgeFirewallRuleEntity]


class VmwareEdgeNatRuleEntity(TypedDict):
    id: int  # noqa: WPS125
    vcloud_id: str
    description: str
    type: str  # noqa: WPS125
    original_ip: str
    translated_ip: str
    protocol: str
    original_port: str
    translated_port: str
    enabled: bool


class VmwareEdgeVpnTunnelEntity(TypedDict):
    id: int  # noqa: WPS125
    vcloud_id: str
    enabled: bool
    name: str
    description: str
    local_id: str
    local_ip: str
    local_subnets: List[str]
    peer_identificator: str
    peer_endpoint: str
    peer_subnets: List[str]
    mtu: int
    perfect_forward_secrecy: bool
    encryption_type: str
    digest_algorithm: str
    diffie_hellman_group: str


class VmwareEdgeVpnEntity(TypedDict):
    enabled: bool
    tunnels: List[VmwareEdgeVpnTunnelEntity]
