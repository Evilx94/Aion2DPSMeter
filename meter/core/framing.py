"""AION frame container candidate, driven by migration/specs/framing.md."""
from dataclasses import dataclass
from .binary import Cursor,InvalidData,raw_lz4
@dataclass(frozen=True)
class Message:
    opcode:bytes
    body:bytes
    offset:int
    depth:int=0

def messages(data,depth=0,_budget=None):
    budget=_budget if _budget is not None else [32*1024*1024]
    if depth>5:raise InvalidData('nesting limit')
    cursor=Cursor(data)
    while cursor.remaining:
        start=cursor.position
        if data[start]==0:cursor.take(1);continue
        advertised=cursor.variable();width=cursor.position-start
        size=advertised+width-4
        if not width+2<=size<=65535:raise InvalidData('frame length')
        inner=Cursor(cursor.take(size-width))
        lead=inner.uint(1)
        opcode=inner.take(2) if 240<=lead<=254 else bytes([lead])+inner.take(1)
        payload=inner.take(inner.remaining)
        if opcode!=bytes([255,255]):
            yield Message(opcode,payload,start,depth);continue
        packed=Cursor(payload);length=packed.uint(4)
        if length==0:raise InvalidData('empty bundle')
        budget[0]-=length
        if budget[0]<0:raise InvalidData("expanded byte budget")
        plain=raw_lz4(packed.take(packed.remaining),length)
        yield from messages(plain,depth+1,budget)
