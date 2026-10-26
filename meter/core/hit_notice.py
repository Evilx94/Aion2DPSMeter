"""Landed-hit evidence, never a damage amount.

Layout documented by AionMeter.Core PacketParser.ParseHitNotice; existing
reference attribution in THIRD-PARTY-NOTICES.md applies. Full records checked
against the independently recorded Nahma capture on 2026-10-23.
"""
from dataclasses import dataclass
import math,struct
from .binary import Cursor,InvalidData
from .damage import checked_entity

@dataclass(frozen=True)
class HitNotice:
    actor:int
    target:int
    skill:int
    sequence:int
    uid:int
    index:int
    subindex:int

def hit_notice(body):
    c=Cursor(body);actor=checked_entity(c)
    if c.uint(1)!=0:raise InvalidData('hit notice marker')
    target=checked_entity(c);skill=c.uint(4)
    if actor==target or not 1<=skill<=299999999:raise InvalidData('hit notice identity')
    sequence=c.uint(1);uid=c.uint(4)
    position=struct.unpack('<fff',c.take(12));c.variable()
    index=c.uint(4);subindex=c.uint(2)
    if c.remaining or any(not math.isfinite(v) or abs(v)>=10000000 for v in position):
        raise InvalidData('hit notice position/tail')
    return HitNotice(actor,target,skill,sequence,uid,index,subindex)
