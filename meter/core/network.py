"""Passive TCP ACK timing. No probes, payload decoding or loss-percentage guesses."""
from collections import deque
from dataclasses import dataclass
from statistics import median


@dataclass(frozen=True)
class TcpObservation:
    source:str
    destination:str
    source_port:int
    destination_port:int
    sequence:int
    acknowledgement:int
    flags:int
    payload_size:int|None
    time_ms:int


class TcpTelemetry:
    def __init__(self):
        self.select(None)
    def select(self,key):
        self.key=key;self.origin=None;self.highest=None;self.probe=None
        self.samples=deque(maxlen=20);self.time=-1;self.repeated_segments=0
    def invalidate(self):
        self.probe=None;self.samples.clear()
    def relative(self,sequence):
        reference=self.highest or 0
        return reference+(sequence-(self.origin+reference)+2**31)%2**32-2**31
    def observe(self,p):
        if p is None or self.key is None:return
        flow=(p.source,p.source_port,p.destination,p.destination_port)
        reverse=(self.key[2],self.key[3],self.key[0],self.key[1])
        if flow not in (self.key,reverse):return
        if p.time_ms<self.time:return
        self.time=p.time_ms
        if p.flags&4:self.invalidate();return
        if flow==reverse:
            if p.payload_size is None:
                # Offload/truncation makes sequence consumption unknown.
                self.probe=None;return
            size=p.payload_size+bool(p.flags&2)+bool(p.flags&1)
            if size<=0:return # pure client ACK is not a round-trip probe
            if self.origin is None:self.origin=p.sequence;self.highest=0
            start=self.relative(p.sequence);end=start+size
            contiguous=start==self.highest
            if start<self.highest:
                # May be retransmission, capture duplication or reordering.
                # Karn: do not time an ambiguously acknowledged transmission.
                self.repeated_segments+=1
                if self.probe:self.probe[3]=True
            elif start>self.highest:
                self.probe=None # missing outgoing capture; no length invented
            self.highest=max(self.highest,end)
            if self.probe is None and contiguous:
                self.probe=[start,end,p.time_ms,False]
        elif p.flags&16 and self.probe is not None:
            ack=self.relative(p.acknowledgement)
            if ack>self.highest:self.probe=None;return
            if ack<self.probe[1]:return
            _,_,sent,ambiguous=self.probe;self.probe=None
            elapsed=p.time_ms-sent
            if not ambiguous and 0<elapsed<=10000:self.samples.append((p.time_ms,elapsed))
    def snapshot(self,now=None):
        now=max(self.time,now if now is not None else self.time)
        recent=[value for stamp,value in self.samples if 0<=now-stamp<=10000]
        return {'tcp_rtt_ms':median(recent) if recent else None,
                'rtt_samples':len(recent),'rtt_age_ms':now-self.samples[-1][0] if self.samples else None,
                'repeated_client_segments':self.repeated_segments,
                'packet_loss_percent':None,'measurement':'passive_tcp_ack'}
