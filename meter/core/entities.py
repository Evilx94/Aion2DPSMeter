"""Strict entity lifecycle records; unknown optional data is not fabricated."""
from dataclasses import dataclass
from .binary import Cursor,InvalidData
from .damage import checked_entity

@dataclass(frozen=True)
class Health:
    entity:int
    kind:int
    current:int
    maximum:int=0

def remain_health(payload):
    c=Cursor(payload);entity=checked_entity(c);kind=c.variable();c.variable();c.variable()
    if kind not in (1,2):raise InvalidData('unconfirmed health kind')
    width=8 if kind==2 else 4
    hp=c.uint(width)
    if c.remaining:
        # Repeated own observations: type-2 snapshot repeats the same u64 after tag 07.
        if kind!=2 or c.remaining!=9 or c.uint(1)!=7 or c.uint(8)!=hp:
            raise InvalidData('unconfirmed health extension')
    if hp>10000000000:raise InvalidData('health range')
    return Health(entity,kind,hp)

def health_pair(payload):
    c=Cursor(payload);entity=checked_entity(c);hp=c.variable();maximum=c.variable()
    if c.remaining or maximum==0 or hp>maximum:raise InvalidData('unconfirmed health pair')
    return Health(entity,0,hp,maximum)

def death(payload):
    c=Cursor(payload);entity=checked_entity(c);c.variable();flag=c.variable()
    if c.remaining:raise InvalidData('unconfirmed death extension')
    # 7 is a removal/despawn, not evidence of a kill.
    if flag not in (1,3,7):raise InvalidData('unconfirmed death flag')
    return entity,{1:'already_dead',3:'death',7:'despawn'}[flag]

def kill_credit(payload):
    c=Cursor(payload);entity=checked_entity(c);middle=c.uint(4);killer=c.variable()
    if middle==0 and killer==0:return entity,'despawn',None
    if not 1<=killer<=9999999:return entity,'death',None
    # Death is already established. Incomplete optional identity must not erase it.
    try:
        server=c.uint(2);length=c.uint(1);name=c.take(length).decode('utf-8')
    except (InvalidData,UnicodeError):return entity,'death',None
    if not 1000<=server<3000 or not name or len(name)>16 or not name.isalnum():return entity,'death',None
    return entity,'death',(killer,name,server)

def battle(payload,time):
    c=Cursor(payload);entity=checked_entity(c);c.variable();active=c.variable()
    if active not in (0,1):raise InvalidData('battle toggle')
    deadline=None
    if active and c.remaining==8:
        deadline=c.uint(8)
        if time is None or not time<deadline<=time+3600000:raise InvalidData('battle deadline')
    if c.remaining:raise InvalidData('battle extension')
    return entity,bool(active),deadline

@dataclass(frozen=True)
class NpcSpawn:
    entity:int
    template:int
    position:tuple
    hp_candidate:int=0

def npc_spawn(payload):
    """Unique template/coordinate record; repeated spawn HP is tentative until verified."""
    import math,struct
    c=Cursor(payload);entity=checked_entity(c);kind=c.uint(1);start=c.position
    if kind not in (0x04,0x0c,0x0d,0x1c):return None
    if kind==0x04 and payload[c.position:c.position+2]!=bytes([0x20,0]):return None
    choices=[]
    for at in range(start+3,min(start+64,len(payload)-14)):
        if payload[at:at+3] not in (bytes([0,0,2]),bytes([0,64,2]),bytes([0,64,3])):continue
        template=int.from_bytes(payload[at-3:at],'little')
        position=struct.unpack('<fff',payload[at+3:at+15])
        if not template or any(not math.isfinite(value) or abs(value)>=10000000 for value in position):continue
        candidates=set()
        for offset in range(at+19,min(at+43,len(payload)-2)):
            if payload[offset]!=1:continue
            try:
                hp=Cursor(payload,offset+1);current=hp.variable();maximum=hp.variable()
                if current==maximum and 101<=maximum<=10000000000:candidates.add(maximum)
            except InvalidData:pass
        candidate=next(iter(candidates)) if len(candidates)==1 else 0
        choices.append(NpcSpawn(entity,template,position,candidate))
    if len(choices)!=1:return None
    return choices[0]
