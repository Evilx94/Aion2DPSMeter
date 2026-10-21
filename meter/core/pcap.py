"""Classic PCAP + incoming AION Ethernet/IPv4/TCP reader using the standard library.
No packet-library import. PCAPNG/IPv6/fragment reassembly are explicitly unsupported.
"""
from dataclasses import dataclass
from struct import unpack
from .binary import InvalidData
@dataclass(frozen=True)
class Segment:
    source:str
    destination:str
    source_port:int
    destination_port:int
    sequence:int
    flags:int
    payload:bytes
    time_ms:int

def ethernet_tcp(frame,time_ms):
    if len(frame)<14:raise InvalidData('truncated Ethernet')
    kind=int.from_bytes(frame[12:14],'big');at=14
    for _ in range(2):
        if kind not in (0x8100,0x88a8):break
        if at+4>len(frame):raise InvalidData('truncated VLAN')
        kind=int.from_bytes(frame[at+2:at+4],'big');at+=4
    if kind!=0x800:return None
    if len(frame)<at+20:raise InvalidData('truncated IPv4')
    version=frame[at]>>4;ip_header=(frame[at]&15)*4
    if version!=4 or ip_header<20:raise InvalidData('invalid IPv4 header')
    # Filter a demonstrably different TCP direction before checking its payload
    # length. Outgoing offload frames may have IP total length zero. Never infer
    # or repair that length; only the incoming 13328 stream is relevant here.
    tcp=at+ip_header
    fragment=int.from_bytes(frame[at+6:at+8],'big')
    if frame[at+9]==6 and not fragment&0x3fff and tcp+20<=len(frame) and int.from_bytes(frame[tcp:tcp+2],'big')!=13328:return None
    total=int.from_bytes(frame[at+2:at+4],'big')
    if total<ip_header or at+total>len(frame):raise InvalidData('truncated IP payload')
    if frame[at+9]!=6:return None
    fragment=int.from_bytes(frame[at+6:at+8],'big')
    if fragment&0x3fff:raise InvalidData('fragmented IPv4 unsupported')
    source='.'.join(str(b) for b in frame[at+12:at+16]);destination='.'.join(str(b) for b in frame[at+16:at+20])
    tcp=at+ip_header
    if tcp+20>at+total:raise InvalidData('truncated TCP header')
    header=(frame[tcp+12]>>4)*4
    if header<20 or tcp+header>at+total:raise InvalidData('invalid TCP header')
    return Segment(source,destination,int.from_bytes(frame[tcp:tcp+2],'big'),int.from_bytes(frame[tcp+2:tcp+4],'big'),
                   int.from_bytes(frame[tcp+4:tcp+8],'big'),frame[tcp+13],frame[tcp+header:at+total],time_ms)

def capture_records(path):
    with open(path,'rb') as source:
        header=source.read(24)
        if len(header)!=24:raise InvalidData('truncated PCAP header')
        formats={bytes.fromhex('d4c3b2a1'):('<',1000),bytes.fromhex('a1b2c3d4'):('>',1000),
                 bytes.fromhex('4d3cb2a1'):('<',1000000),bytes.fromhex('a1b23c4d'):('>',1000000)}
        if header[:4] not in formats:raise InvalidData('unsupported PCAP format')
        order,divisor=formats[header[:4]];major,minor,zone,sigfigs,snaplen,link=unpack(order+'HHIIII',header[4:])
        if (major,minor)!=(2,4) or link!=1:raise InvalidData('PCAP requires Ethernet 2.4')
        if not 0<snaplen<=16*1024*1024:raise InvalidData('PCAP snaplen limit')
        while True:
            info=source.read(16)
            if not info:return
            if len(info)!=16:raise InvalidData('truncated PCAP record header')
            seconds,fraction,captured,original=unpack(order+'IIII',info)
            if captured>snaplen or captured>original or fraction>=divisor*1000:raise InvalidData('invalid PCAP record')
            frame=source.read(captured)
            if len(frame)!=captured:raise InvalidData('truncated PCAP record data')
            yield frame,seconds*1000+fraction//divisor
