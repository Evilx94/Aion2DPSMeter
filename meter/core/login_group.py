"""Login group records confirmed in the 2026-10-14 field-raid capture.

No search through combat bodies: only the explicit social-state opcodes below.
Opaque statistics are not interpreted as damage or equipment.
"""
from dataclasses import dataclass
import re
from .binary import Cursor,InvalidData

@dataclass(frozen=True)
class LoginGroup:
    key:int
    own_group:int
    capacity:int
    rows:tuple
    raid:bool=False
    declared_groups:int=1

def member(payload,allowed_flags=(0,3)):
    from .parser import text,wire_class
    c=Cursor(payload);flags=c.uint(1);slot=c.uint(1);entity=c.uint(4)
    if flags not in allowed_flags or not 1<=slot<=5 or not 0<=entity<=9999999:raise InvalidData('login member header')
    record_server=c.uint(2);instance_server=c.uint(2)
    if not 1<=record_server<=9999 or not 1<=instance_server<=9999 or c.uint(1)!=36:raise InvalidData('login member marker')
    uuid=c.take(36)
    if not re.fullmatch(rb'[0-9A-Fa-f]{8}(?:-[0-9A-Fa-f]{4}){3}-[0-9A-Fa-f]{12}',uuid):raise InvalidData('login member uuid')
    identifier=c.uint(8);server=identifier>>48
    if server!=record_server or not identifier&((1<<48)-1):raise InvalidData('login member character id')
    name=text(c,c.uint(1));class_id=c.uint(4);cls=wire_class(class_id)
    if not cls:raise InvalidData('login member class')
    c.variable();c.variable() # observed current/max HP, not combat events
    # Bounded 19 October party/raid records also carry status 02 and 04.
    # These are opaque social metadata, not damage or presence guarantees.
    if not 24<=c.remaining<=256 or payload[-1] not in (0,1,2,3,4,5):raise InvalidData('login member tail')
    return {'id':entity,'slot':slot,'character_id':identifier,'name':name,'server':server,'class_id':class_id,'class':cls}

def members(payload,count):
    # A record has an exact UUID marker six bytes after its start. Require a
    # unique complete set, not the first plausible name in an arbitrary body.
    if count==0:
        if payload:raise InvalidData('login empty group tail')
        return ()
    starts=[m.start()-10 for m in re.finditer(rb'\x24[0-9A-Fa-f]{8}(?:-[0-9A-Fa-f]{4}){3}-[0-9A-Fa-f]{12}',payload) if m.start()>=10]
    if len(starts)!=count or not starts or starts[0]!=0:raise InvalidData('login roster record boundaries')
    ends=starts[1:]+[len(payload)]
    rows=tuple(member(payload[a:b]) for a,b in zip(starts,ends))
    if len({r['slot'] for r in rows})!=count:raise InvalidData('login roster duplicate slot')
    ids=[r['id'] for r in rows if r['id']]
    if len(set(ids))!=len(ids) or len({r['character_id'] for r in rows})!=count:raise InvalidData('login roster duplicate identity')
    return rows

def snapshot(op,payload):
    if len(payload)>8192:raise InvalidData('login roster body limit')
    c=Cursor(payload)
    prefix=c.uint(1)
    if prefix not in (0,9) or (prefix==9 and op!=bytes.fromhex('0092')):raise InvalidData('login roster prefix')
    key=c.uint(8)
    if not key:raise InvalidData('login roster key')
    if op==bytes.fromhex('0092'):
        leader=c.uint(8);capacity_value=c.uint(4);variant=c.take(4)
        if capacity_value!=5 or not ((leader==0 and variant==bytes.fromhex('02010202')) or (leader!=0 and variant==bytes.fromhex('02010002'))):raise InvalidData('login party variant')
        if prefix==9:
            # 20 October four-person party: an explicit 130-byte extension
            # precedes the member count. The eight-byte token is opaque.
            # Require the observed fixed structure; do not scan for a count
            # or assume that all five capacity slots contain players.
            extension=c.take(130)
            if not leader or extension[0]!=0 or extension[9:13]!=(5).to_bytes(4,'little') or any(extension[13:]):raise InvalidData('extended login party block')
        count=c.uint(1);own_group=key;capacity=5;declared_groups=1
        trailers=(1,3,5) if leader else (3,5,9)
        # 19 October: a zero-leader, one-member snapshot ends in 06 and is
        # immediately corroborated by an own-member update. Keep this narrow;
        # the parser still requires matching live local identity metadata.
        if not leader and count==1:trailers=trailers+(6,)
        if leader and count==1:trailers=trailers+(0,)
        if not 1<=count<=5 or payload[-1] not in trailers:raise InvalidData('login roster count/trailer')
        rows=members(payload[c.position:-1],count)
        if leader and leader not in {r['character_id'] for r in rows}:raise InvalidData('login party leader missing')
    else:
        leader=c.uint(8)
        if not leader or c.uint(1)!=0 or c.uint(4)!=20 or c.take(3) not in (bytes.fromhex('020102'),bytes.fromhex('020104')):raise InvalidData('login raid variant')
        declared_groups=c.uint(1)
        if not 1<=declared_groups<=4 or payload[-1] not in (1,3,5,9):raise InvalidData('login raid variant')
        starts=[];tag=(key>>32).to_bytes(4,'little');at=payload.find(tag,c.position+4)
        while at>=0:
            start=at-4
            if start>=c.position and at+10<=len(payload) and 1<=payload[at+4]<=4 and int.from_bytes(payload[at+5:at+9],'little')==5 and payload[at+9]<=5:starts.append(start)
            at=payload.find(tag,at+4)
        if len(starts)!=declared_groups or starts[0]!=c.position:raise InvalidData('login raid group boundaries')
        rows=[];keys=[];ordinals=[]
        for start,end in zip(starts,starts[1:]+[len(payload)-1]):
            part=Cursor(payload,start);group_key=part.uint(8)
            # The server can serialize subgroups as 1,3,2. Their ordinal is
            # identity metadata, not a required position in the message.
            ordinal=part.uint(1)
            if not 1<=ordinal<=4 or ordinal in ordinals or part.uint(4)!=5:raise InvalidData('login raid group')
            ordinals.append(ordinal)
            count=part.uint(1)
            keys.append(group_key)
            rows.extend({**r,'login_group_key':group_key} for r in members(payload[part.position:end],count))
        if len(set(keys))!=declared_groups:raise InvalidData('login raid duplicate group')
        own_group=keys[0];capacity=20;rows=tuple(rows)
    ids=[r['id'] for r in rows if r['id']]
    if len(set(ids))!=len(ids) or len({r['character_id'] for r in rows})!=len(rows):raise InvalidData('login roster duplicate identity')
    return LoginGroup(key,own_group,capacity,rows,capacity==20,declared_groups)

def update(op,payload):
    if len(payload)>512:raise InvalidData('login member body limit')
    if op==bytes.fromhex('0a96'):
        c=Cursor(payload);key=c.uint(8)
        return key,member(payload[c.position:])
    # The own-subgroup update also carries mask 07, paired with a keyed
    # mask-03 raid update for the identical member in the 15 October capture.
    return None,member(payload,allowed_flags=(0,3,7))

class LoginMembership:
    def __init__(self,snapshot,generation):
        self.snapshot=snapshot;self.generation=generation
        self.rows={(r.get('login_group_key',snapshot.own_group),r['slot']):r for r in snapshot.rows}
    def add(self,key,row):
        key=self.snapshot.own_group if key is None else key
        if key>>32!=self.snapshot.key>>32 or (not self.snapshot.raid and key!=self.snapshot.key):raise InvalidData('login member unrelated group')
        groups={k for k,slot in self.rows}|{key}
        if len(groups)>self.snapshot.capacity//5:raise InvalidData('login group capacity')
        candidate={**self.rows,(key,row['slot']):row}
        ids=[r['id'] for r in candidate.values() if r['id']]
        if len(set(ids))!=len(ids) or len({r['character_id'] for r in candidate.values()})!=len(candidate):raise InvalidData('login member duplicate identity')
        self.rows=candidate
    def complete(self):
        return len(self.rows)==self.snapshot.capacity or (self.snapshot.raid and self.snapshot.declared_groups==4)

class PartialOwnGroup(LoginMembership):
    """Own-subgroup updates anchored by a confirmed local member; no invented key."""
    def __init__(self,row,generation):
        self.snapshot=LoginGroup(None,None,5,(),False,1)
        self.generation=generation
        self.rows={(None,row['slot']):row}
    def add(self,key,row):
        if key is not None:raise InvalidData('partial group has no confirmed raid key')
        candidate={**self.rows,(None,row['slot']):row}
        ids=[r['id'] for r in candidate.values() if r['id']]
        if len(set(ids))!=len(ids) or len({r['character_id'] for r in candidate.values()})!=len(candidate):
            raise InvalidData('login member duplicate identity')
        self.rows=candidate
    def complete(self):
        # Updates do not establish the full roster or its vacancies, even at five.
        return False
