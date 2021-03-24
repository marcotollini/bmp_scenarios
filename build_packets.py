from basic_sim_model import BasicSimulation, BGPId, PathAttributes
import ipaddress
from pydantic import BaseModel
from bmp import (
    BMPHeader,
    BMPInitiation,
    PerPeerHeader,
    BMPInformationTLV,
    BMPPeerUpNotificationInfo,
    BMPPeerUp,
    BMPRouteMonitoring,
    TLVPathStatus,
    TLVPathStatusEnterprise,
    BMPTLVPaolo,
)
from bgp import (
    BGP,
    BGPOpen,
    BGPOptParam,
    BGPCapFourBytesASN,
    BGPCapMultiprotocol,
    BGPCapGeneric,
    BGPHeader,
    BGPUpdate,
    BGPPathAttr,
    BGPPAOrigin,
    BGPPAASPath,
    BGPPAMultiExitDisc,
    BGPPALocalPref,
    BGPPANextHop,
    BGPPAAS4BytesPath,
    BGPPACommunity,
    BGPNLRI_IPv4,
    BGPPAExtComms,
    BGPPAExtCommunity,
    BGPPAExtCommTwoOctetASSpecific,
)
from typing import Optional, List, Dict, Sequence, Any


def build_open_msg(bgp_info: BGPId):
    standard_cap = BGPCapMultiprotocol(afi=1, safi=1)
    route_refresh = BGPCapGeneric(code=2)
    asn_capability = BGPCapFourBytesASN(asn=bgp_info.asn)

    if bgp_info.asn > 65535:
        my_asn = 23456
    else:
        my_asn = bgp_info.asn
    return BGPHeader() / BGPOpen(
        my_as=my_asn,
        hold_time=180,
        bgp_id=bgp_info.bgp_id,
        opt_params=[
            BGPOptParam(
                param_type=2, param_value=[standard_cap, route_refresh, asn_capability]
            )
        ],
    )


def ip4_or_ipv6_to_str(ip: ipaddress._BaseAddress) -> str:
    """
    Not sure if there is anything on ipaddress already providing this.
    """
    ip = ipaddress.ip_address(ip)
    if ip.version == 4:
        return f"::{ip}"
    return str(ip)


def create_bgp_update(path: PathAttributes, prefixes: Sequence[str]):
    """
    Creates a bgp update for a set of prefixesand path attributes
    """
    lp_attr = BGPPathAttr(
        type_flags="Transitive",
        type_code=5,
        attribute=BGPPALocalPref(local_pref=path.lp),
    )
    origin_attr = BGPPathAttr(
        type_flags="Transitive", type_code=1, attribute=BGPPAOrigin(origin="IGP")
    )
    next_hop_attr = BGPPathAttr(
        type_flags="Transitive",
        type_code=3,
        attribute=BGPPANextHop(next_hop=path.next_hop),
    )
    med_attr = BGPPathAttr(
        type_flags="Optional", type_code=4, attribute=BGPPAMultiExitDisc(med=path.med)
    )
    # do as_path
    as_path_attr = BGPPathAttr(
        type_flags="Transitive",
        type_code=2,
        attribute=BGPPAAS4BytesPath(
            segments=[
                BGPPAAS4BytesPath.ASPathSegment(
                    segment_type=2, segment_value=path.as_path
                )
            ]
        ),
    )
    comm_attr = BGPPathAttr(
        type_flags="Transitive+Optional",
        type_code=8,
        attribute=BGPPACommunity(communities=path.communities),
    )
    attributes = [
        origin_attr,
        as_path_attr,
        next_hop_attr,
        med_attr,
        lp_attr,
        comm_attr,
    ]
    nlris = [BGPNLRI_IPv4(prefix=p) for p in prefixes]
    return BGPHeader() / BGPUpdate(path_attr=attributes, nlri=nlris)


class BMPSimPackets(BaseModel):
    initialization: Any
    peers_up: List[Any]
    updates: List[Any]

    def __eq__(self, other):
        if len(self.peers_up) != len(other.peers_up) or len(self.updates) != len(other.updates):
            return False
        if bytes(self.initialization) != bytes(other.initialization):
            return False
        for n, p in enumerate(self.peers_up):
            if bytes(p) != bytes(other.peers_up[n]):
                return False
        for n, p in enumerate(self.updates):
            if bytes(p) != bytes(other.updates[n]):
                return False
        return True


def build_packets(sim: BasicSimulation) -> BMPSimPackets:
    """
    Builds the packets to send from a basic model.
    """

    local_info = sim.local_info
    local_bgp = sim.local_bgp
    local_asn = local_bgp.asn
    peers = sim.peers

    # Find the available prefixes for connections.
    prefix_for_connection = ipaddress.IPv4Network(sim.prefix_for_connection)
    diff_for_sub = 31 - prefix_for_connection.prefixlen
    available_link_prefies = prefix_for_connection.subnets(diff_for_sub)

    prefix_info = sim.attributes_per_peer
    peer_status = sim.status_per_prefix

    # Build initiation msg
    initiation_msg = BMPHeader() / BMPInitiation(
        information=[
            BMPInformationTLV(Type=1, information=local_info.sys_descr),
            BMPInformationTLV(Type=2, information=local_info.sys_name),
        ]
    )

    open_sent = build_open_msg(local_bgp)

    # Calculate msgs per peer
    per_peer_per_peer = {}
    monitoring_per_peer = {}
    for peerid, peer in peers.items():
        link_net = next(available_link_prefies)
        local_ip, external_ip = list(link_net.hosts())[0:2]

        external_ip_str = ip4_or_ipv6_to_str(external_ip)
        local_ip_str = ip4_or_ipv6_to_str(local_ip)

        per_peer_header = PerPeerHeader(
            peer_address=external_ip_str,
            peer_asn=peer.asn,
            peer_bgp_id=int(ipaddress.IPv4Address(peer.bgp_id)),
            timestamp_seconds=1594819095,
            timestamp_microseconds=956000,
        )

        received_open = build_open_msg(peer)

        peer_up_info = BMPPeerUpNotificationInfo(
            local_address=local_ip_str,
            local_port=179,
            remote_port=4900,
            sent_open=open_sent,
            received_open=received_open,
        )

        peer_up = BMPHeader() / BMPPeerUp(
            per_peer_header=per_peer_header, info=peer_up_info
        )

        per_peer_per_peer[peer] = peer_up

        # now for the monitoring

        update = create_bgp_update(path=prefix_info[peerid], prefixes=sim.prefixes)

        # Create the tlvs
        tlvs = []
        for prefix, status in peer_status[peerid].items():
            prefix_index = sim.prefixes.index(prefix)

            # select packet type
            tlv_packet = TLVPathStatus
            packet_type = 0
            if sim.tlv_commpany:
                tlv_packet = TLVPathStatusEnterprise
                packet_type = 32768
            status_packet = tlv_packet(
                index=prefix_index, status=status.status, reason=status.reason
            )
            prefix_tlv = BMPTLVPaolo(type=packet_type, value=status_packet)
            tlvs.append(prefix_tlv)

        monitoring = BMPHeader() / BMPRouteMonitoring(
            per_peer=per_peer_header, bgp_update=update, tlv=tlvs
        )
        monitoring_per_peer[peer] = monitoring

    return BMPSimPackets(
        initialization=initiation_msg,
        peers_up=list(per_peer_per_peer.values()),
        updates=list(monitoring_per_peer.values()),
    )
