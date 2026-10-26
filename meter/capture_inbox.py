"""Bounded FIFO between capture and decoding; loss boundaries preserve order."""
from collections import deque
from threading import Condition

class CaptureInbox:
    def __init__(self,max_packets=8192,max_bytes=64*1024*1024):
        self.max_packets=max_packets;self.max_bytes=max_bytes;self.items=deque();self.condition=Condition()
        self.bytes=0;self.packets=0;self.pending_loss=0;self.dropped=0;self.peak_packets=0;self.peak_bytes=0
    def put(self,packet):
        original=getattr(packet,'original',None);size=len(original) if original else len(packet)
        with self.condition:
            if self.packets>=self.max_packets or self.bytes+size>self.max_bytes:
                self.pending_loss+=1;self.dropped+=1;self.condition.notify();return False
            if self.pending_loss:
                self.items.append(('loss',self.pending_loss,0));self.pending_loss=0
            self.items.append(('packet',packet,size));self.packets+=1;self.bytes+=size
            self.peak_packets=max(self.peak_packets,self.packets);self.peak_bytes=max(self.peak_bytes,self.bytes)
            self.condition.notify();return True
    def take(self,timeout=0):
        with self.condition:
            if not self.items and not self.pending_loss and timeout:self.condition.wait(timeout)
            if self.items:
                kind,value,size=self.items.popleft()
                if kind=='packet':self.packets-=1;self.bytes-=size
                return kind,value
            if self.pending_loss:
                value=self.pending_loss;self.pending_loss=0;return 'loss',value
            return None
    def empty(self):
        with self.condition:return not self.items and not self.pending_loss
    def snapshot(self):
        with self.condition:return {'queued_packets':self.packets,'queued_bytes':self.bytes,'peak_packets':self.peak_packets,'peak_bytes':self.peak_bytes,'dropped_packets':self.dropped,'max_packets':self.max_packets,'max_bytes':self.max_bytes}
