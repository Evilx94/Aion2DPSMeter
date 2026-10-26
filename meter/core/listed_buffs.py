"""Bounded port of credited A2Tools abnormal.rs listed-entry/listed layouts."""
from .binary import Cursor,InvalidData
from .damage import checked_entity
from .activity import BuffRecord

def listed_buffs(opcode,body):
    if opcode not in (bytes.fromhex('4136'),bytes.fromhex('4536'),bytes.fromhex('3336')) or len(body)>8192:return ()
    c=Cursor(body)
    try:entity=checked_entity(c)
    except InvalidData:return ()
    start=c.position;after=b'\x07\x02' if opcode==bytes.fromhex('4136') else b'\x0f';cache={};work=0
    def entry(at):
        if at in cache:return cache[at]
        try:
            q=Cursor(body,at);flags=q.uint(1)
            if flags not in (0x10,0x11,0x13):raise InvalidData('listed flags')
            instance=q.variable();abnormal=q.uint(4)
            duration=int.from_bytes(q.take(8),'little',signed=True);end=int.from_bytes(q.take(8),'little',signed=True)
            caster=q.variable() if flags&1 else 0;q.uint(1);skill=q.uint(4) if flags&2 else 0
            if not 1<=abnormal<1000000000 or not 0<=caster<=9999999 or not 0<=skill<=299999999:raise InvalidData('listed identity')
            if duration==-1:
                if end!=4102412400000:raise InvalidData('listed permanent')
            elif not (0<=duration<=400*86400000 and 1704067200000<=end<4102412400000 and end-duration>=1704067200000):raise InvalidData('listed timer')
            result=(BuffRecord(entity,'listed',instance,abnormal,duration,end,caster,skill),q.position)
        except InvalidData:result=None
        cache[at]=result;return result
    readings=[]
    for at in range(start,len(body)-22):
        count=body[at]
        if not count or count*34>len(body)-at or entry(at+1) is None:continue
        paths=[((),at+1)]
        for index in range(count):
            nxt=[]
            for rows,pos in paths:
                parsed=entry(pos)
                if parsed is None:continue
                record,position=parsed
                for skip in (0,1):
                    end=position+skip+12;work+=1
                    if work>20000:return ()
                    if end>len(body):continue
                    # Listed positions are opaque, including captured sentinel floats.
                    fits=entry(end) is not None if index+1<count else body[end:end+len(after)]==after
                    if fits:nxt.append((rows+(record,),end))
            if not nxt or len(nxt)>4:paths=[];break
            paths=nxt
        if len(paths)==1:
            rows=paths[0][0]
            if len({r.instance for r in rows})!=len(rows):continue
            readings.append(rows)
            if len(readings)>1:return ()
    return readings[0] if len(readings)==1 else ()

