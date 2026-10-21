"""Own-capture specification for the recurring 4a/36 character-stat envelope.
Numeric attributes stay opaque: this decoder provides no damage or names.
"""
from dataclasses import dataclass
from .binary import Cursor,InvalidData
from .damage import checked_entity

@dataclass(frozen=True)
class LocalUpdate:
    entity:int
    attributes:tuple
    tail:bytes

def local_update(payload):
    c=Cursor(payload);entity=checked_entity(c);count=c.uint(1)
    if count>96 or c.remaining!=count*6+8:raise InvalidData('unconfirmed local stat envelope')
    attributes=[];seen=set()
    for _ in range(count):
        key=c.uint(2);value=c.uint(4)
        if not 1<=key<=4095 or key in seen:raise InvalidData('unconfirmed local attribute')
        seen.add(key);attributes.append((key,value))
    # This tail can be nonzero. Its semantics are not guessed.
    return LocalUpdate(entity,tuple(attributes),c.take(8))
