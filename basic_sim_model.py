from pydantic import BaseModel
from pydantic.dataclasses import dataclass as pyd_dataclass
from typing import Optional, Dict, List

class MyBaseModel(BaseModel):
    '''
    BaseModel not allowing mutations and with a hash.
    '''
    class Config:
        allow_mutation = False

    def __hash__(self):
        return hash((type(self),) + tuple(self.__dict__.values()))

class BMPLocal(MyBaseModel):
    '''
    Description of a system.
    '''
    sys_descr: str
    sys_name: str

class PeerConection(MyBaseModel):
    '''
    Description of a peer
    '''
    local_ip: str
    remote_ip: str
    local_port: Optional[int]
    remote_port: Optional[int]

class BGPId(MyBaseModel):
    '''
    BGP ID
    '''
    bgp_id: str
    asn: int

class PathAttributes(MyBaseModel):
    '''
    Basic path attributes.
    '''
    lp: int = 100
    med: int = 0
    as_path: List[int] = []
    next_hop: str
    communities: List[int] = [] # "normal" communities


class BMPPathStatus(MyBaseModel):
    '''
    Status. Note we dont validate yet if the strings actually correspond to the 
    BMP specification.
    '''
    status: List[str] = []
    reason: Optional[str] = None

# For simplicity, peers and prefixes are strings.
PeerId = str
Prefix = str

class BasicSimulation(MyBaseModel):
    '''
    A basic simulation containing N peers announcing  M Ipv4 prefixes.
    '''

    # if yes, we use the company ttl type with some PEM. The rest is the same.
    tlv_commpany: bool = False

    local_info: BMPLocal
    local_bgp: BGPId

    # peers are identified by a string, it must be consistent with the rest of values.
    peers: Dict[PeerId, BGPId]

    # Prefix for connection is a IP address that we will use to connect all peers.
    prefix_for_connection: Prefix

    # The prefixes we will use
    prefixes: List[Prefix]

    # attributes for peers that will be applied for all prefixes
    attributes_per_peer: Dict[PeerId, PathAttributes]

    # Status per peer/prefix
    status_per_prefix: Dict[PeerId, Dict[Prefix, BMPPathStatus]]

