"""Bounded late identity reconciliation for hits inside an observed fight.

Membership is frozen at hit time. A later exact current PlayerInfo/character-ID
link is required; class, target and pull order never establish membership.
"""
from collections import deque
from copy import copy,deepcopy
from dataclasses import replace

class DeferredDamage:
    LIMIT=10000
    TTL=600000
    ARCHIVE_LIMIT=100000
    def __init__(self,ledger):
        self.ledger=ledger;self.rows=deque();self.archives={};self.revision=0;self.recovered=set()
    def queue(self,time,hit):
        l=self.ledger;w=l.world
        if not l.active or not w.party_trusted or not w.party_known or w.party_source=='status_recovery':return
        if l.integrity!='ok' or hit.kind!='damage' or hit.amount<=0 or w.self_entity is None or w.local_conflict:return
        if hit.source in w.summons or hit.source in w.npcs or hit.source==hit.target:return
        if hit.target in w.people or hit.target in w.summons or hit.target in w.retired:return
        if not any(e.kind=='damage' and e.target==hit.target for e in l.active):return
        person=w.people.get(hit.source)
        if not person or not person.class_name or person.confirmed:return
        witnesses=tuple((r['character_id'],r['name'],r['server'],r['class']) for r in w.party_records
            if type(r.get('character_id')) is int and 0<r['character_id']<2**64
            and r['character_id']>>48==r.get('server') and r.get('class')==person.class_name)
        if not witnesses:return
        from .combat import Entry
        from .damage_sections import target_category
        entry=Entry(time,hit.source,'',hit.skill,hit.amount,class_name=person.class_name,
            source_entity=hit.source,periodic=hit.periodic,target=hit.target,critical=hit.critical,
            hits=1+hit.extra_hits,target_kind='npc' if hit.target in w.npcs else 'unknown',
            target_category=target_category(w.npcs.get(hit.target)))
        self.trim(time)
        if len(self.rows)>=self.LIMIT:return
        self.rows.append((l.sequence+1,tuple(w.identity_token(hit.source)),tuple(w.identity_token(hit.target)),
                          w.self_entity,tuple(w.identity_token(w.self_entity)),entry,witnesses))
        l.fight_partial=True
        self.revision+=1
    def trim(self,time):
        w=self.ledger.world
        self.rows=deque(r for r in self.rows if r[1][0]==w.generation and 0<=time-r[5].time<=self.TTL)
        needed={r[0] for r in self.rows}
        valid={f['id'] for f in self.ledger.closed}
        self.archives={k:v for k,v in self.archives.items() if k in needed and k in valid}
    def archive(self):
        l=self.ledger;identifier=l.sequence
        if not any(r[0]==identifier for r in self.rows):return
        while self.archives and sum(len(a.active) for a in self.archives.values())+len(l.active)>self.ARCHIVE_LIMIT:
            oldest=min(self.archives);self.archives.pop(oldest)
            self.rows=deque(r for r in self.rows if r[0]!=oldest)
        if len(l.active)>self.ARCHIVE_LIMIT:
            self.rows=deque(r for r in self.rows if r[0]!=identifier);return
        shadow=copy(l);shadow.active=list(l.active);shadow.active_actors=set(l.active_actors);shadow.actor_equipment=deepcopy(l.actor_equipment)
        shadow.issues=l.issues.copy();shadow.actor_issues=l.actor_issues.copy()
        shadow.cast_events=deque(l.cast_events);shadow.cast_assigned=set(l.cast_assigned);shadow.buffs=deepcopy(l.buffs)
        shadow.world=copy(l.world)
        targets={e.target for e in l.active};shadow.world.npcs=deepcopy({k:v for k,v in l.world.npcs.items() if k in targets})
        self.archives[identifier]=shadow
    def reconcile(self,time):
        if time is None:return
        l=self.ledger;w=l.world;self.trim(time);remaining=deque();changed=set()
        closed={f['id']:f for f in l.closed}
        for row in self.rows:
            identifier,source_token,target_token,own,own_token,entry,witnesses=row
            if (tuple(w.identity_token(entry.actor))!=source_token or tuple(w.identity_token(entry.target))!=target_token
                or w.self_entity!=own or tuple(w.identity_token(own))!=own_token or not w.party_trusted or w.local_conflict):continue
            historical=closed.get(identifier)
            target=l if identifier==l.sequence+1 and l.active else self.archives.get(identifier)
            if target is None or (historical and historical['integrity']!='ok') or target.integrity!='ok':continue
            # An explicit departure revokes pending candidates. Never use a
            # matching class or a cached name as a substitute for PlayerInfo.
            current={r.get('character_id') for r in w.party_records}
            witnesses=tuple(r for r in witnesses if r[0] in current)
            if not witnesses:continue
            person=w.people.get(entry.actor);link=w.party_links.get(entry.actor);payload=w.player_records.get(entry.actor)
            matches=[r for r in witnesses if link==(r[1],r[2],r[0]) and payload
                and payload.count(r[0].to_bytes(8,'little'))==1 and person and person.confirmed
                and person.name==r[1] and person.class_name==r[3] and person.server in (0,r[2])]
            if len(matches)!=1 or not w.authorized(entry.actor):remaining.append(row);continue
            if len(target.active)>=target.max_events:continue
            # Queueing starts only after an accepted hit. Thus these historical
            # hits never invent a fight or extend its observed time boundaries.
            if not target.active[0].time<=entry.time<=target.last_damage:remaining.append(row);continue
            accepted=replace(entry,name=person.name,name_source=person.name_source,actor_server=matches[0][2])
            l.unassigned.consume(identifier,source_token,entry)
            target.active.append(accepted);target.active_actors.add(entry.actor)
            equipment=l.equipment(entry.actor)
            if equipment:target.actor_equipment[entry.actor]=equipment
            target.fight_partial=True;target.issues['identity_deferred']+=1;changed.add(identifier)
        self.rows=remaining
        for identifier in changed:
            target=self.archives[identifier] if identifier in closed else l
            target.active.sort(key=lambda e:e.time)
            if identifier in closed:
                shadow=self.archives[identifier];previous=closed[identifier]
                updated=shadow.summary(shadow.active,previous['reason'],identifier)
                previous.clear();previous.update(updated)
        if changed:self.revision+=1;self.recovered.update(changed)
