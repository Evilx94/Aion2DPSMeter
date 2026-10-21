"""Scapy/Npcap adapter for the new core. Scapy remains an intended dependency."""
from .pcap import Segment
from .binary import InvalidData


def observation(packet):
    """Header-only telemetry; invalid outgoing lengths never reach combat/loss."""
    from scapy.layers.inet import IP,TCP
    from .network import TcpObservation
    if IP not in packet or TCP not in packet:return None
    ip=packet[IP];tcp=packet[TCP]
    if int(tcp.sport)!=13328 and int(tcp.dport)!=13328:return None
    if int(ip.frag) or int(ip.flags)&1:return None
    if ip.ihl is None or tcp.dataofs is None or int(ip.ihl)<5 or int(tcp.dataofs)<5:return None
    length=int(ip.len or 0)-int(ip.ihl)*4-int(tcp.dataofs)*4
    size=length if 0<=length<=len(tcp.payload) else None
    return TcpObservation(ip.src,ip.dst,int(tcp.sport),int(tcp.dport),int(tcp.seq),int(tcp.ack),int(tcp.flags),size,int(packet.time*1000))

def segment(packet):
    from scapy.layers.inet import IP,TCP
    if IP not in packet or TCP not in packet:return None
    ip=packet[IP];tcp=packet[TCP]
    # Only the incoming AION stream is decoded. Outgoing NIC-offload captures
    # can have IP length zero; they must not invalidate incoming raid metadata.
    if int(tcp.sport)!=13328:return None
    if int(ip.frag) or int(ip.flags)&1:raise InvalidData('fragmented IPv4 unsupported')
    length=int(ip.len)-int(ip.ihl)*4-int(tcp.dataofs)*4
    if length<0:raise InvalidData('invalid IP length')
    payload=bytes(tcp.payload)[:length]
    if len(payload)!=length:raise InvalidData('truncated captured payload')
    return Segment(ip.src,ip.dst,int(tcp.sport),int(tcp.dport),int(tcp.seq),int(tcp.flags),payload,int(packet.time*1000))

def replay(path,session):
    from scapy.all import PcapReader
    with PcapReader(str(path)) as capture:
        for packet in capture:
            try:item=segment(packet)
            except InvalidData:
                session.stats['packets']+=1;session.stats['malformed_packet']+=1;session.loss();continue
            session.packet(item)
            session.network.observe(observation(packet))
    if session.stream:session.stream.flush_gap()
    session.ledger.finish('capture_end')
