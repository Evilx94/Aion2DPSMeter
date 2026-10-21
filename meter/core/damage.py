"""Bounded direct/periodic decoding with explicit classification provenance.
Reference protocol/data notices are retained in THIRD-PARTY-NOTICES.md.
"""
from dataclasses import dataclass
from .binary import Cursor,InvalidData
@dataclass(frozen=True)
class Hit:
    source:int
    target:int
    skill:int
    amount:int
    scalar:int=0
    critical:bool=False
    extra_hits:int=0
    kind:str='damage'
    periodic:bool=False
    supplementary:int|None=None
@dataclass(frozen=True)
class Decision:
    status:str
    hits:tuple=()
    reason:str=''

def checked_entity(cursor):
    number=cursor.variable()
    if not 1<=number<=9999999:raise InvalidData('entity range')
    return number

def record(payload,start):
    cursor=Cursor(payload,start);target=checked_entity(cursor)
    control=cursor.variable();layout=control&15
    if layout==0:return None,cursor.position,'cast_marker'
    if layout not in (4,6):raise InvalidData('unsupported layout '+str(layout))
    record_flags=cursor.variable();source=checked_entity(cursor)
    skill=cursor.uint(4)
    if not 1<=skill<=299999999:raise InvalidData('skill range')
    cursor.take(1);category=cursor.variable();metadata=cursor.position
    options=set()
    for displacement in ([8] if layout==4 else [10,11]):
        try:
            values=Cursor(payload,metadata+displacement)
            scalar=values.variable();amount=values.variable()
            if scalar==0:scalar=amount;amount=values.variable()
            # Unconfirmed damage-first special form is deliberately not guessed.
            if not 1<=amount<=99999999 or not (scalar==0 or 1000<=scalar<=200000):continue
            endings=[]
            for has_extra_field in ([True,False] if layout==4 else [False]):
                tail=Cursor(payload,values.position)
                try:
                    if has_extra_field and not 1<=tail.variable()<=25:continue
                    count=0
                    if control&32:
                        count=tail.variable()
                        if not 1<=count<=25:continue
                        amounts=[tail.variable() for _ in range(count)]
                        if sum(amounts)>=amount:continue
                    end=tail.position;remaining=payload[end:];supplementary=None
                    if record_flags&4 and remaining.startswith(bytes([1,0])) and len(remaining)>2:
                        supplement=Cursor(payload,end+2);value=supplement.variable()
                        # Only a complete terminal field, never a guessed partial record.
                        if supplement.remaining==0:
                            supplementary=value;end=supplement.position;remaining=b''
                    if remaining.startswith(bytes([3,0])):
                        suffix=Cursor(payload,end+2)
                        if suffix.remaining:suffix.variable()
                        end=suffix.position;remaining=payload[end:]
                    # Self-delimiting opaque token vector observed on NPC and pet skills.
                    # Keep its values opaque: they never add damage or hit counts.
                    if 1000000<=skill<3000000 and remaining:
                        terminal=remaining
                        if record_flags&16 and terminal.endswith(bytes([1])):
                            terminal=terminal[:-1]
                        if len(terminal)>=2 and terminal[-1]==0 and terminal[-2]>0:
                            vector=(1<=terminal[0]<=16 and len(terminal)==1+4*terminal[0]+2)
                            if len(terminal)==2 or vector:
                                end=len(payload);remaining=b''
                    if remaining and not (remaining.startswith(bytes([1,0])) or (len(remaining)>=2 and remaining[1]==0 and 1<=remaining[0]<=7)):
                        continue
                    endings.append((end,count,supplementary))
                except InvalidData:continue
            for end,count,supplementary in endings:options.add((scalar,amount,end,count,supplementary))
        except InvalidData:continue
    if not options:raise InvalidData('unconfirmed values or tail')
    if len(options)!=1:raise InvalidData('ambiguous values or boundary')
    scalar,amount,end,count,supplementary=options.pop()
    return Hit(source,target,skill,amount,scalar,category==3,count,'heal' if source==target else 'damage',supplementary=supplementary),end,'accepted'

def damage_message(payload):
    at=0;result=[]
    try:
        while at<len(payload):
            if payload[at:at+2]==bytes([1,0]):at+=2
            elif result:break
            hit,end,status=record(payload,at)
            if status=='cast_marker':return Decision(status)
            result.append(hit)
            if end<=at:raise InvalidData('no progress')
            at=end
            if payload[at:]==bytes([1,0]):break
        return Decision('accepted',tuple(result)) if result else Decision('rejected',reason='empty payload')
    except InvalidData as error:
        # An uncertain chained record invalidates this message transaction.
        return Decision('rejected',reason=str(error))


@dataclass(frozen=True)
class PeriodicFields:
    source:int
    target:int
    effect:int
    skill:int
    values:tuple
    related_skill:int|None

def periodic_fields(payload):
    cursor=Cursor(payload);target=checked_entity(cursor);effect=cursor.uint(1)
    if effect not in (1,2,8,9,10,11):raise InvalidData('unknown periodic effect')
    source=checked_entity(cursor);cursor.variable();encoded=cursor.uint(4);skill=encoded//100
    if not 1<=skill<=299999999:raise InvalidData('periodic skill range')
    # Reference ProtocolTests identifies 0x08 as a non-damage buff tick.
    # Own Draupnir packets have no amount: only an exact terminal skill u32.
    # Do not count this marker as damage or as measured buff uptime.
    if effect==8:
        if cursor.remaining!=4:raise InvalidData('unconfirmed non-damage periodic tail')
        related=cursor.uint(4)
        if not 1<=related<=299999999:raise InvalidData('related skill range')
        return PeriodicFields(source,target,effect,skill,(),related)
    # Captured 9/10/11 forms have a trailing u32. Its meaning is not guessed.
    if effect in (9,10,11) and cursor.remaining>=5:
        value_bytes=cursor.take(cursor.remaining-4);related=cursor.uint(4)
        fields=Cursor(value_bytes);values=[]
        while fields.remaining:values.append(fields.variable())
        expected=2 if effect==11 else 1
        if len(values)!=expected:raise InvalidData('unconfirmed periodic field count')
        if not 1<=related<=299999999:raise InvalidData('related skill range')
    else:
        values=[cursor.variable()];related=None
        if cursor.remaining:raise InvalidData('unconfirmed periodic tail')
    if any(not 1<=value<=99999999 for value in values):raise InvalidData('periodic value range')
    return PeriodicFields(source,target,effect,skill,tuple(values),related)

def periodic_message(payload,policy):
    try:
        fields=periodic_fields(payload)
        if fields.effect==8:return Decision('ignored',reason='non-damage periodic marker')
        if len(fields.values)!=1:
            return Decision('unclassified',reason='two periodic values need gameplay meaning')
        amount=fields.values[0]
        if fields.effect in (1,9,11):kind='heal'
        elif fields.source==fields.target or not policy.damage_dot(fields.skill):
            return Decision('unclassified',reason='periodic damage skill not confirmed')
        else:kind='damage'
        return Decision('accepted',(Hit(fields.source,fields.target,fields.skill,amount,kind=kind,periodic=True),))
    except InvalidData as error:return Decision('rejected',reason=str(error))
