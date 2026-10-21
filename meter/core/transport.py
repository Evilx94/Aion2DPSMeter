"""Bounded incremental TCP bytes; no gap filling. No old AION imports."""
from collections import Counter
class Stream:
    def __init__(self,sink,loss,conflict,sequence,limit=8*1024*1024,history_limit=1024*1024):
        self.sink=sink;self.loss=loss;self.conflict=conflict;self.origin=sequence;self.next=0;self.last_delivery=0
        self.pending={};self.delivered={};self.history_start=0;self.limit=limit;self.history_limit=history_limit;self.stats=Counter();self.conflict_offsets=set();self.delivery_start=0
    def push(self,sequence,data,time):
        start=(sequence-self.origin+2**31)%2**32-2**31
        if len(data)>self.limit:raise ValueError('segment limit')
        disputed=False;self.conflict_offsets=set()
        for at,value in enumerate(data,start):
            if at<self.next:
                if at in self.delivered and self.delivered[at]!=value:disputed=True;self.conflict_offsets.add(at)
                elif at not in self.delivered:
                    # History cannot prove equivalence, so do not silently trust it.
                    self.stats['unverifiable_retransmission']+=1
                    disputed=True;self.conflict_offsets.add(at)
                else:self.stats['duplicates']+=1
                continue
            if at in self.pending:
                previous,stamp=self.pending[at]
                if previous!=value:self.pending[at]=(None,stamp);self.stats['conflicting_bytes']+=1
                else:self.stats['duplicates']+=1
            else:self.pending[at]=(value,time)
        if disputed:self.conflict();self.stats['delivered_conflicts']+=1
        if len(self.pending)>self.limit:
            self.pending.clear();self.loss();raise ValueError('pending limit')
        self.drain()
    def drain(self):
        ready=bytearray();stamp=self.last_delivery;self.delivery_start=self.next
        while self.next in self.pending:
            value,time=self.pending.pop(self.next)
            if value is None:
                if ready:self.sink(bytes(ready),stamp)
                self.last_delivery=stamp;ready.clear()
                self.conflict_offsets={self.next};self.conflict();self.next+=1;self.delivery_start=self.next;continue
            ready.append(value);stamp=max(stamp,time);self.delivered[self.next]=value;self.next+=1
        if ready:self.sink(bytes(ready),stamp)
        self.last_delivery=stamp
        lower=self.next-self.history_limit
        while self.history_start<lower:
            self.delivered.pop(self.history_start,None);self.history_start+=1
    def flush_gap(self):
        if not self.pending:return
        first=min(self.pending)
        if first>self.next:
            self.stats['gap_events']+=1
            self.stats['gap_bytes']+=first-self.next;self.next=first;self.delivered.clear();self.history_start=self.next;self.loss()
        self.drain()
