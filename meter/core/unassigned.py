"""Unassigned entity observations, separate from authorized group totals."""
from collections import deque
from dataclasses import dataclass

@dataclass(frozen=True)
class Observation:
    fight:int
    token:tuple
    time:int
    actor:int
    target:int
    skill:int
    amount:int
    kind:str
    periodic:bool
    critical:bool
    extra_hits:int
    class_name:str

class UnassignedEntities:
    LIMIT=20000
    def __init__(self,ledger):
        self.ledger=ledger;self.rows={};self.index={};self.serial=0;self.names={};self.spans={}
    @staticmethod
    def key(fight,token,time,actor,target,skill,amount,kind,periodic,critical,extra_hits):
        return (fight,token,time,actor,target,skill,amount,kind,periodic,critical,extra_hits)
    def remove(self,serial):
        self.spans.pop(serial,None)
        row=self.rows.pop(serial,None)
        if row is None:return
        key=self.key(row.fight,row.token,row.time,row.actor,row.target,row.skill,row.amount,row.kind,row.periodic,row.critical,row.extra_hits)
        queue=self.index[key]
        if queue and queue[0]==serial:queue.popleft()
        else:queue.remove(serial)
        if not queue:self.index.pop(key)
    def observe(self,time,hit):
        l=self.ledger;w=l.world;person=w.people.get(hit.source)
        if not l.active or l.integrity!='ok' or hit.amount<=0 or not person or not person.class_name:return
        if hit.source in w.summons or hit.source in w.npcs or hit.source in w.retired:return
        if hit.kind=='damage':
            if hit.target in w.people or hit.target in w.summons or hit.target in w.retired:return
            if not any(e.kind=='damage' and e.target==hit.target for e in l.active):return
        elif hit.kind=='heal':
            if hit.target!=w.self_entity and not w.authorized(hit.target):return
        else:return
        while len(self.rows)>=self.LIMIT:self.remove(next(iter(self.rows)))
        token=tuple(w.identity_token(hit.source));fight=l.sequence+1;self.serial+=1
        row=Observation(fight,token,time,hit.source,hit.target,hit.skill,hit.amount,hit.kind,hit.periodic,hit.critical,hit.extra_hits,person.class_name)
        self.rows[self.serial]=row
        key=self.key(fight,token,time,hit.source,hit.target,hit.skill,hit.amount,hit.kind,hit.periodic,hit.critical,hit.extra_hits)
        self.index.setdefault(key,deque()).append(self.serial)
    def bind_frames(self,previous,start,end):
        for serial in range(previous+1,self.serial+1):
            if serial in self.rows:self.spans[serial]=(start,end)
    def conflict(self,offsets):
        for serial,(start,end) in list(self.spans.items()):
            if any(start<=at<end for at in offsets):self.remove(serial)
    def consume(self,fight,token,entry):
        key=self.key(fight,token,entry.time,entry.actor,entry.target,entry.skill,entry.damage,entry.kind,entry.periodic,entry.critical,entry.hits-1)
        ids=self.index.get(key)
        if ids:self.remove(ids[0])
    def refresh_identity(self,entity):
        w=self.ledger.world;person=w.people.get(entity);token=tuple(w.identity_token(entity))
        if person and person.confirmed and person.name and any(r.actor==entity and r.token==token for r in self.rows.values()):
            self.names[(token,entity)]=person.name
    def annotate(self,fights):
        w=self.ledger.world;valid={f['id'] for f in fights};groups={}
        for serial,row in list(self.rows.items()):
            if row.fight not in valid:self.remove(serial);continue
            person=w.people.get(row.actor)
            if tuple(w.identity_token(row.actor))==row.token and person and person.confirmed and person.name:
                self.names[(row.token,row.actor)]=person.name
            key=(row.fight,row.token,row.actor)
            actor=groups.setdefault(key,{'id':row.actor,'name':self.names.get((row.token,row.actor),''),
                'class':row.class_name,'identity_token':list(row.token),'damage':0,'healing':0,'events':0,
                'first_ms':row.time,'last_ms':row.time,'group_confirmed':False,'damage_targets':{}})
            actor['name']=self.names.get((row.token,row.actor),'');actor[row.kind=='heal' and 'healing' or 'damage']+=row.amount
            actor['events']+=1;actor['last_ms']=max(actor['last_ms'],row.time)
            if row.kind=='damage':
                target=actor['damage_targets'].setdefault(row.target,{'id':row.target,'damage':0,'last_ms':row.time})
                target['damage']+=row.amount;target['last_ms']=max(target['last_ms'],row.time)
        live={(r.token,r.actor) for r in self.rows.values()}
        self.names={k:v for k,v in self.names.items() if k in live}
        for fight in fights:
            if fight.get('tracking_scope')=='self':continue
            actors=[a for (identifier,token,actor),a in groups.items() if identifier==fight['id']]
            if not actors:continue
            for a in actors:
                seconds=max(1,(max(fight['last_damage_ms'],a['last_ms'])-fight['start_ms'])/1000)
                a['dps']=a['damage']/seconds;a['hps']=a['healing']/seconds
                a['damage_targets']=list(a['damage_targets'].values())
                if fight.get('integrity','ok')!='ok':a['dps']=None;a['hps']=None;a['unreliable']=True
            fight['unassigned_actors']=sorted(actors,key=lambda a:(-a['damage'],-a['healing'],a['id']))
            fight['unassigned_in_group_totals']=False
        return fights
