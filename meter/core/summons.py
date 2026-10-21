"""Named summon metadata established from controlled Cleric captures.

Only the observed 1f/00/01 form is supported. NPC self-ID repetitions and
guild labels are not ownership evidence. Unknown forms remain unsupported.
"""
from dataclasses import dataclass
from .binary import Cursor, InvalidData
from .damage import checked_entity

@dataclass(frozen=True)
class Summon:
    entity: int
    name: str
    owner: int
    server: int = 0
    evidence: str = "named_owner"

def named_summon(payload):
    cursor = Cursor(payload)
    entity = checked_entity(cursor)
    kind = cursor.uint(1)
    if kind != 0x1f:
        return None
    if len(payload) > 4096 or cursor.take(2) != bytes([0, 1]):
        raise InvalidData('unconfirmed named summon header')
    length = cursor.uint(1)
    try:
        name = cursor.take(length).decode('utf-8')
    except UnicodeError as error:
        raise InvalidData('summon name UTF8') from error
    if not name or len(name) > 16 or not name.isalnum():
        raise InvalidData('summon name invalid')
    # Require exactly one complete typed owner record after the name.
    marker = bytes([7, 2, 6])
    starts = [at for at in range(cursor.position, len(payload)-2)
              if payload[at:at+3] == marker]
    if len(starts) != 1:
        raise InvalidData('missing or ambiguous summon owner')
    at = starts[0]
    if at+8 > len(payload) or payload[at+7] != 2:
        raise InvalidData('truncated or unconfirmed summon owner')
    owner = int.from_bytes(payload[at+3:at+7], 'little')
    if not 1 <= owner <= 9999999 or owner == entity:
        raise InvalidData('summon owner range')
    return Summon(entity, name, owner)

def paired_parent(payload,entity,kind,position):
    """Only the observed 10/00 forms, with two agreeing parent references.

    Generic NPC self references and unowned effects use different forms and
    cannot establish a player owner. No timing or power-score inference.
    """
    if kind not in (0x1f,0x1d,0x5d) or payload[position:position+2]!=bytes([16,0]) or len(payload)>4096:return None
    anchor=bytes.fromhex('8075d52abb030000')
    positions=[at for at in range(position,len(payload)-7) if payload[at:at+8]==anchor]
    if len(positions)!=1:return None
    c=Cursor(payload,positions[0]+8)
    parent=checked_entity(c)
    if parent==entity:return None
    hints=[]
    if kind==0x1f:
        for at in range(c.position,len(payload)-7):
            if payload[at:at+2]!=bytes([7,2]) or payload[at+2] not in (1,6) or payload[at+7]!=3:continue
            hints.append((int.from_bytes(payload[at+3:at+7],'little'),0))
    else:
        for at in range(c.position,len(payload)-5):
            if payload[at:at+2]!=bytes([9,1]):continue
            key=int.from_bytes(payload[at+2:at+6],'little');server=0
            if kind==0x5d and at+15<=len(payload) and payload[at+10:at+12]==bytes(2):
                candidate=int.from_bytes(payload[at+12:at+14],'little');length=payload[at+14]
                if 1000<=candidate<3000 and 1<=length<=48 and at+15+length<=len(payload):
                    try:guild=payload[at+15:at+15+length].decode('utf-8')
                    except UnicodeError:continue
                    if not guild.isprintable():continue
                    server=candidate
            if 1<=key<=9999999:hints.append((key,server))
    if len(hints)!=1 or hints[0][0]!=parent:return None
    return Summon(entity,'',parent,hints[0][1],'paired_parent')

def spawn_role(payload):
    """Typed helpers. Inline owner names require a unique identity in this zone."""
    c=Cursor(payload);entity=checked_entity(c);kind=c.uint(1)
    try:paired=paired_parent(payload,entity,kind,c.position)
    except InvalidData:paired=None
    if paired is not None:return paired
    if kind in (0x1f,0x1c):
        position=c.position
        if c.remaining>=3 and payload[position:position+2]==bytes([0,1]):
            c.take(2);length=c.uint(1)
            try:name=c.take(length).decode('utf-8')
            except UnicodeError as error:raise InvalidData('helper UTF8') from error
            if not name or len(name)>16 or not name.isalnum():raise InvalidData('helper name')
            if kind==0x1f:
                if bytes([7,2,6]) in payload[c.position:]:
                    try:return named_summon(payload)
                    except InvalidData:return Summon(entity,'',0,evidence='unresolved_named')
            return Summon(entity,name,0,evidence='inline_name')
        if kind==0x1f:return Summon(entity,'',0,evidence='unresolved_named')
        return None
    if kind==0x5f:
        if len(payload)>4096:raise InvalidData('spawn size')
        hints=[]
        for at in range(c.position+1,len(payload)-12):
            if payload[at-1]!=6 or payload[at+8:at+10]!=bytes(2):continue
            parent=int.from_bytes(payload[at:at+4],'little');server=int.from_bytes(payload[at+10:at+12],'little');length=payload[at+12]
            if not 1<=parent<=9999999 or parent==entity or not 1000<=server<3000 or not 1<=length<=48 or at+13+length>len(payload):continue
            try:guild=payload[at+13:at+13+length].decode('utf-8')
            except UnicodeError:continue
            if not guild.isprintable():continue
            hints.append((parent,server))
        if len(hints)==1:return Summon(entity,'',hints[0][0],hints[0][1],'parent_server')
        return Summon(entity,'',0,evidence='unresolved_parent')
    if kind in (0x1d,0x5d):return Summon(entity,'',0,evidence='unresolved_effect')
    return None
