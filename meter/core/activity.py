"""Observed casts and strict buff lifecycle records, separate from damage totals.

Wire layouts checked against A2Tools abnormal.rs (c9cf6551), itself crediting
Seralth/Daevalog. Sources and existing license notices are retained.
"""
from dataclasses import dataclass
from collections import deque,Counter
from functools import lru_cache
from pathlib import Path
from statistics import median
import json,math,struct,heapq
from .binary import Cursor,InvalidData
from .damage import checked_entity

@dataclass(frozen=True)
class Cast:
    actor:int
    skill:int
    sequence:int
    kind:int
    target:int

def cast_record(body):
    c=Cursor(body);actor=checked_entity(c);flag=c.variable();skill=c.uint(4)
    if not 1<=skill<=299999999:raise InvalidData('cast skill range')
    sequence=c.uint(1);kind=c.uint(1);target=c.variable()
    if kind not in (0,2) or target>9999999:raise InvalidData('unconfirmed cast type/target')
    # The remaining positional/optional fields are not cast counters.
    return Cast(actor,skill,sequence,kind,target)

@dataclass(frozen=True)
class BuffRecord:
    entity:int
    operation:str
    instance:int=0
    abnormal:int=0
    duration:int=-1
    end:int=0
    caster:int=0
    skill:int=0
    removals:tuple=()

def buff_record(opcode,body):
    c=Cursor(body);entity=checked_entity(c)
    if opcode==bytes.fromhex('2c38'):
        count=c.uint(1);removals=[]
        for _ in range(count):
            kind=c.uint(1);instance=c.variable();reason=c.uint(1)
            if kind&7==7:
                c.variable();c.uint(4);c.uint(4)
            removals.append((instance,reason))
        if c.remaining:raise InvalidData('buff removal tail')
        return BuffRecord(entity,'remove',removals=tuple(removals))
    if opcode==bytes.fromhex('2a38') and c.uint(1)!=1:raise InvalidData('buff add count')
    flags=c.uint(1)
    if flags not in (0x11,0x13):raise InvalidData('unconfirmed buff flags')
    instance=c.variable();abnormal=c.uint(4)
    duration=int.from_bytes(c.take(8),'little',signed=True);end=int.from_bytes(c.take(8),'little',signed=True)
    caster=c.variable();level=c.uint(1);skill=c.uint(4) if flags&2 else 0
    c.uint(1);position=struct.unpack('<fff',c.take(12))
    if c.remaining or not 1<=abnormal<1000000000 or not 0<=caster<=9999999 or not 0<=skill<=299999999:
        raise InvalidData('buff identity/tail')
    if duration < -1 or duration>400*86400000 or any(not math.isfinite(x) or abs(x)>=10000000 for x in position):
        raise InvalidData('buff duration/position')
    if duration==-1:
        if end!=4102412400000:raise InvalidData('buff permanent timer')
    elif not 1704067200000<=end<4102412400000 or end-duration<1704067200000:
        raise InvalidData('buff timer range')
    return BuffRecord(entity,'add' if opcode==bytes.fromhex('2a38') else 'change',instance,abnormal,duration,end,caster,skill)

@lru_cache(maxsize=1)
def buff_catalog():
    try:
        from ..catalog_store import records
        return {r['abnormal']:{k:v for k,v in r.items() if not k.startswith('_') and k!='builtin'} for r in records('buff_labels.json','records')}
    except (OSError,ValueError,KeyError,TypeError):return {}

class BuffTracker:
    def __init__(self):
        self.live={};self.timers=[];self.timer_version=0;self.closed=deque(maxlen=20000);self.offsets=deque(maxlen=64);self.revision=0;self.issues=Counter();self.pending_lists={}
    def reset(self):
        self.live.clear();self.timers.clear();self.closed.clear();self.offsets.clear();self.revision+=1;self.issues.clear();self.pending_lists.clear()
    def close(self,key,time,reason):
        self.pending_lists.pop(key,None)
        state=self.live.pop(key,None)
        if state is None:return
        end=min(time,state['expires']) if state['expires'] is not None else time
        if len(self.closed)==self.closed.maxlen:self.issues['history_limit']+=1
        self.closed.append({**state,'to':max(state['from'],end),'reason':reason});self.revision+=1
    def schedule(self,key,state):
        self.timer_version+=1;state['timer_version']=self.timer_version
        if state['expires'] is not None:heapq.heappush(self.timers,(state['expires'],self.timer_version,key))
        if len(self.timers)>30000:
            self.timers=[(v['expires'],v['timer_version'],k) for k,v in self.live.items() if v['expires'] is not None]
            heapq.heapify(self.timers)
    def expire(self,time):
        while self.timers and self.timers[0][0]<=time:
            expires,version,key=heapq.heappop(self.timers);state=self.live.get(key)
            if state and state['timer_version']==version:self.close(key,expires,'timer')
    def gone(self,entity,time):
        self.pending_lists={k:v for k,v in self.pending_lists.items() if k[0]!=entity}
        for key in list(self.live):
            if key[0]==entity:self.close(key,time,'entity_end')
    def accept(self,record,time):
        self.expire(time)
        if record.operation=='remove':
            for instance,reason in record.removals:self.close((record.entity,instance),time,'removed:'+str(reason))
            return
        key=(record.entity,record.instance);old=self.live.get(key)
        if record.operation=='add' and record.duration>=0:
            self.offsets.append(time-(record.end-record.duration))
            pending=self.pending_lists;self.pending_lists={}
            for previous,stamp in pending.values():self.accept(previous,stamp)
            old=self.live.get(key)
        expires=None
        if record.duration>=0:
            if old and old.get('server_end') and old['expires'] is not None:
                expires=old['expires']+(record.end-old['server_end']) if old['expires'] is not None else None
            elif self.offsets:expires=int(record.end+median(self.offsets))
            else:
                if record.operation=='listed':
                    if len(self.pending_lists)<10000:
                        previous=self.pending_lists.get(key)
                        stamp=previous[1] if previous and previous[0]==record else time
                        self.pending_lists[key]=(record,stamp)
                    self.issues['listed_without_clock']+=1;return
                if old:self.close(key,time,'timer_changed_without_clock')
                self.issues['unseen_change_without_clock']+=1;return
        if old and record.operation=='change' and old['abnormal']==record.abnormal and old['caster']==record.caster:
            old.update(expires=expires,server_end=record.end,skill=record.skill or old['skill']);self.schedule(key,old);self.revision+=1;return
        if old:self.close(key,time,'replaced')
        label=buff_catalog().get(record.abnormal,{})
        limit=label.get('stack_limit')
        if type(limit) is int and limit>0:
            siblings=[(k,v) for k,v in self.live.items() if k[0]==record.entity and v['abnormal']==record.abnormal]
            while len(siblings)>=limit:
                oldest=min(siblings,key=lambda item:item[1]['from']);self.close(oldest[0],time,'stack_limit');siblings.remove(oldest)
        if len(self.live)>=10000:self.issues['live_limit']+=1;return
        self.live[key]={'actor':record.entity,'abnormal':record.abnormal,'caster':record.caster,'skill':record.skill,
                        'from':time,'expires':expires,'server_end':record.end,'observed_only':True}
        self.schedule(key,self.live[key]);self.revision+=1
    def listed(self,records,time):
        if not records:return
        entity=records[0].entity;present={(entity,r.instance) for r in records}
        for key in list(self.live):
            if key[0]==entity and key not in present:self.close(key,time,'not_listed')
        for key in list(self.pending_lists):
            if key[0]==entity and key not in present:self.pending_lists.pop(key,None)
        for record in records:self.accept(record,time)
    def summary(self,start,end,actors):
        if end<=start:return []
        groups={}
        for state in list(self.closed)+list(self.live.values()):
            if state['actor'] not in actors:continue
            stop=state.get('to',end)
            if state['expires'] is not None:stop=min(stop,state['expires'])
            left=max(start,state['from']);right=min(end,stop)
            if right<=left:continue
            key=(state['actor'],state['abnormal']);groups.setdefault(key,[]).append((left,right,state))
        result=[]
        for (actor,abnormal),segments in groups.items():
            points=[]
            for left,right,_ in segments:points.extend(((left,1),(right,-1)))
            points.sort();up=0;stacks=0;maximum=0;previous=start
            for time,delta in points:
                if stacks:up+=time-previous
                stacks+=delta;maximum=max(maximum,stacks);previous=time
            label=buff_catalog().get(abnormal,{})
            result.append({'actor':actor,'abnormal':abnormal,'name':label.get('name','?'),'name_source':label.get('source','Nicht zugeordnet'),
                           'uptime_ms':up,'uptime_percent':100*up/(end-start),'max_stacks':maximum,
                           'skill':next((s['skill'] for _,_,s in segments if s['skill']),0),'observed_only':True,
                           'segments':[{'start_ms':a-start,'end_ms':b-start,'caster':s['caster']} for a,b,s in segments]})
        return sorted(result,key=lambda row:(row['actor'],-row['uptime_ms'],row['abnormal']))
