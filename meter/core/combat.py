"""Candidate event ledger: freezes membership and identity at acceptance time."""
from dataclasses import dataclass,asdict
from collections import Counter
from .state import World
@dataclass(frozen=True)
class Entry:
    time:int
    actor:int
    name:str
    skill:int
    damage:int
    kind:str='damage'
    class_name:str=''
    name_source:str=''
    source_entity:int=0
    periodic:bool=False
    target:int=0
    critical:bool=False
    hits:int=1
    target_kind:str='unknown'
    healing_scope:str=''
    actor_server:int=0
    target_category:str='unknown'
class Ledger:
    def __init__(self,world=None,party_only=True,idle_ms=10000,max_events=100000,track_pvp=False,encounters=None):
        from .encounters import EncounterCatalog
        self.encounters=encounters if encounters is not None else EncounterCatalog.builtin();self.location={};self.fight_location={}
        self.world=world or World();self.party_only=party_only;self.track_pvp=track_pvp;self.idle_ms=idle_ms;self.max_events=max_events
        self.active=[];self.active_actors=set();self.actor_equipment={};self.closed=[];self.integrity='ok';self.sequence=0;self.time=-1;self.last_damage=None;self.unresolved_owner_events=0;self.issues=Counter();self.pending_issues=Counter();self.pending_time=None;self.capture_partial=False;self.fight_identity=None;self.fight_partial=False;self.connection_epoch=0;self.unidentified_hits={}
        from collections import deque
        from .activity import BuffTracker
        self.cast_events=deque(maxlen=20000);self.cast_assigned=set();self.buffs=BuffTracker();self.activity_generation=self.world.generation;self.activity_revision=0
        self.set_location(None)
        self.fight_group_state=None
        self.actor_issues=Counter();self.pending_actor_issues=Counter()
    def sync_activity(self):
        if self.activity_generation!=self.world.generation:
            self.cast_events.clear();self.cast_assigned.clear();self.buffs.reset();self.activity_generation=self.world.generation;self.activity_revision+=1
    def equipment(self,actor):
        person=self.world.people.get(actor)
        if not person or not person.confirmed or not self.world.party_trusted:return {}
        server=self.world.player_server(actor)
        matching=[r for r in self.world.party_records if r.get('name')==person.name
                  and (not server or r.get('server')==server) and (not person.class_name or r.get('class')==person.class_name)]
        if len(matching)!=1:return {}
        row=matching[0]
        return {'gear':row.get('gear') if type(row.get('gear')) is int and row['gear']>0 else None,
                'power':row.get('power') if type(row.get('power')) is int and row['power']>0 else None,
                'equipment_source':'server_roster','equipment_character_id':row.get('character_id')}

    def cast(self,time,record):
        self.sync_activity()
        actor=self.world.resolve(record.actor)
        if actor is None or actor!=record.actor or not self.world.authorized(record.actor) or actor in self.world.npcs:return False
        key=(time,record.actor,record.skill,record.sequence,record.kind,record.target)
        if self.cast_events and self.cast_events[-1]['key']==key:return False
        person=self.world.people.get(actor)
        self.cast_events.append({'key':key,'time':time,'actor':actor,'skill':record.skill,'name':person.name if person else '',
                                 'class':person.class_name if person else '', 'name_source':person.name_source if person else '', 'equipment':self.equipment(actor)})
        if self.active:self.active_actors.add(actor)
        self.activity_revision+=1;return True
    def buff(self,time,record):
        self.sync_activity();revision=self.buffs.revision;self.buffs.accept(record,time)
        if self.world.authorized(record.entity) and self.buffs.revision!=revision:self.activity_revision+=1
    def set_location(self,map_id,zone_sequence=0,zone_token=None):
        fact=self.encounters.maps.get(map_id)
        self.location={'map_id':map_id,'dungeon_id':map_id if fact and fact.kind=='dungeon' else None,'dungeon_name':fact.name if fact and fact.kind=='dungeon' else '',
                       'map_name':fact.name if fact else '', 'area_name':fact.name if fact else '', 'area_kind':fact.kind if fact else 'unknown',
                       'region_name':fact.name if fact and fact.kind=='field' else '',
                       'location_source':fact.source if fact else '', 'zone_sequence':zone_sequence,
                       'zone_load_token':zone_token}
    def skipped_without_identity(self,time,hit):
        if self.world.self_entity is not None or hit.kind!='damage':return
        if len(self.unidentified_hits)>=2048 and hit.source not in self.unidentified_hits:self.unidentified_hits.pop(next(iter(self.unidentified_hits)))
        old=self.unidentified_hits.get(hit.source)
        count=old[1]+1 if old and old[0]==self.world.generation else 1
        self.unidentified_hits[hit.source]=(self.world.generation,count,time)
    def identified_self(self,time):
        own=self.world.self_entity
        if own is None or time is None:return
        for source,(generation,count,last) in list(self.unidentified_hits.items()):
            if generation!=self.world.generation or time-last>self.idle_ms:
                self.unidentified_hits.pop(source,None);continue
            if self.world.resolve(source)==own:
                self.issue('identity_late',time=time);self.unidentified_hits.pop(source,None)
    def refresh_identity(self,entity):
        # A later name for the same live entity enriches its open fight only.
        # Closed reports and already named identities remain frozen.
        from dataclasses import replace
        person=self.world.people.get(entity)
        if not person or not person.confirmed or not person.name:return
        self.active=[replace(e,name=person.name,name_source=person.name_source,class_name=e.class_name or person.class_name)
                     if e.actor==entity and (not e.name or (e.name_source=='manual' and e.name.casefold()==person.name.casefold())) else e for e in self.active]
        if self.fight_identity and self.fight_identity.get('id')==entity and not self.fight_identity.get('name'):
            self.fight_identity.update(name=person.name,server=person.server,source=person.name_source)
    def relevant(self,source):
        if not self.party_only:return source not in self.world.npcs
        if self.world.authorized(source):return True
        record=self.world.summons.get(source)
        if not record:return False
        if record.owner and self.world.authorized(record.owner):return True
        own=self.world.people.get(self.world.self_entity)
        return bool(record.name and ((own and record.name==own.name) or
                    (self.world.party_trusted and any(name==record.name for name,server in self.world.members))))
    def issue(self,reason,source=None,time=None):
        if source is not None and not self.relevant(source):return
        actor=self.world.resolve(source) if source is not None else None
        if actor in self.world.summons and actor not in self.world.owners:
            owner=self.world.summons[actor].owner
            actor=owner if owner and self.world.authorized(owner) else None
        if self.active:
            self.issues[reason]+=1
            if actor is not None:self.actor_issues[actor,reason]+=1
        else:
            if time is not None and self.pending_time is not None and time-self.pending_time>self.idle_ms:self.pending_issues.clear();self.pending_actor_issues.clear()
            self.pending_issues[reason]+=1;self.pending_time=time
            if actor is not None:self.pending_actor_issues[actor,reason]+=1
    def accept(self,time,hit):
        if time is None:raise ValueError('damage needs captured time')
        self.sync_activity()
        if time<self.time:raise ValueError('time reversed')
        self.tick(time)
        group_state=('invalid' if not self.world.party_trusted else ('missing' if not self.world.party_known else ('partial' if not self.world.party_complete else ('members' if self.world.members else 'solo'))))
        if self.active and group_state in ('missing','invalid','partial'):
            self.fight_group_state=group_state
        if hit.source in self.world.retired and hit.source not in self.world.people:return False
        target_npc=self.world.npcs.get(hit.target)
        if hit.kind=='damage' and (hit.target in self.world.retired or (target_npc and target_npc.alive is False)):return False
        if hit.source in self.world.summons and hit.source not in self.world.owners:
            self.skipped_without_identity(time,hit);self.world.unresolved_damage.add(hit.source);self.unresolved_owner_events+=1;self.issue('unresolved_owner',hit.source,time);return False
        if hit.kind=='damage' and (hit.source in self.world.npcs or hit.target in self.world.summons):return False
        if self.integrity!='ok' or hit.kind not in ('damage','heal') or hit.amount<=0:return False
        if hit.kind=='heal' and not self.active:return False
        if self.party_only and not self.world.authorized(hit.source):self.skipped_without_identity(time,hit);return False
        actor=self.world.resolve(hit.source)
        if actor is None or (actor in self.world.retired and actor not in self.world.people) or actor in self.world.npcs or (actor in self.world.summons and actor not in self.world.owners) or (hit.kind=='damage' and actor==hit.target):return False
        if hit.kind=='damage' and self.world.resolve(hit.target) in self.world.people and (not self.track_pvp or self.world.authorized(hit.target)):return False
        if len(self.active)>=self.max_events:self.integrity='event_limit';self.issue('event_limit');return False
        person=self.world.people.get(actor)
        if not self.active:
            self.actor_issues=self.pending_actor_issues.copy();self.pending_actor_issues.clear()
            self.issues=self.pending_issues.copy();self.pending_issues.clear();self.pending_time=None
            own=self.world.people.get(self.world.self_entity)
            self.actor_equipment={}
            self.fight_partial=self.capture_partial
            self.fight_location=dict(self.location)
            self.fight_group_state=group_state
            self.fight_identity={'id':self.world.self_entity,'name':own.name if own else '', 'server':own.server if own else 0, 'source':own.name_source if own else '', 'token':self.world.identity_token(self.world.self_entity)}
        if actor not in self.actor_equipment:
            metadata=self.equipment(actor)
            if metadata:self.actor_equipment[actor]=metadata
        self.active_actors.add(actor)
        healing_scope=('self' if actor==hit.target else ('group' if hit.target in self.world.people and self.world.authorized(hit.target) else 'other')) if hit.kind=='heal' else ''
        from .damage_sections import target_category
        self.active.append(Entry(time,actor,person.name if person else '',hit.skill,hit.amount,hit.kind,person.class_name if person else '',person.name_source if person else '',hit.source,hit.periodic,hit.target,hit.critical,1+hit.extra_hits,'player' if self.world.resolve(hit.target) in self.world.people else ('npc' if hit.target in self.world.npcs else 'unknown'),healing_scope,self.world.player_server(actor),target_category(target_npc)))
        if hit.kind=='damage':self.last_damage=time
        return True
    def health(self,record,time):
        if record.kind==1 or record.entity in self.world.people:
            if record.current>0:self.world.retired.discard(record.entity)
            else:self.entity_end(record.entity,'death',time)
            return
        npc=self.world.npcs.get(record.entity) if record.kind==0 else self.world.npc(record.entity)
        if npc is None:return
        if npc.alive is False and record.current>0:return
        npc.hp=record.current;npc.updated_ms=time
        if record.maximum:npc.max_hp=record.maximum
        elif record.current==npc.spawn_hp_candidate and record.current>0:npc.max_hp=record.current
        if record.current>0:
            npc.alive=True;self.world.retired.discard(record.entity)
        else:self.entity_end(record.entity,'death',time)
    def entity_end(self,entity,reason,time):
        npc=self.world.npcs.get(entity);boss=bool(npc and npc.is_boss)
        self.buffs.gone(entity,time)
        self.world.retire(entity)
        if not self.active:return
        targets={entry.target for entry in self.active if entry.kind=='damage'}
        if entity in targets and (boss or all(target in self.world.retired for target in targets)):
            self.finish('target_death' if reason=='death' else 'target_'+reason)
    def battle(self,entity,active,time):
        npc=self.world.npcs.get(entity) or self.world.npc(entity)
        if npc is None:return
        npc.in_combat=active;npc.updated_ms=time
        if active or not self.active:return
        targets={entry.target for entry in self.active if entry.kind=='damage'}
        if entity in targets and (npc.is_boss or all(t in self.world.npcs and self.world.npcs[t].in_combat is False for t in targets)):
            reset=(npc.max_hp>0 and npc.hp==npc.max_hp) if npc.is_boss else all(self.world.npcs[t].max_hp>0 and self.world.npcs[t].hp==self.world.npcs[t].max_hp for t in targets)
            self.finish('target_reset' if reset else 'combat_left')
    def tick(self,time):
        if time<self.time:raise ValueError('time reversed')
        self.time=time
        if self.pending_time is not None and time-self.pending_time>self.idle_ms:self.pending_issues.clear();self.pending_actor_issues.clear();self.pending_time=None
        if self.last_damage is not None and time-self.last_damage>self.idle_ms:self.finish('idle')
    def finish(self,reason):
        if self.active:
            self.sequence+=1;summary=self.summary(self.active,reason,self.sequence);self.closed.append(summary);self.closed=self.closed[-30:]
            self.cast_assigned.update(event['key'] for event in self.cast_events if summary['start_ms']-1000<=event['time']<=summary['last_damage_ms'])
            self.cast_assigned.intersection_update(event['key'] for event in self.cast_events)
            self.active=[];self.active_actors.clear();self.actor_equipment.clear();self.last_damage=None
        self.capture_partial=False;self.fight_partial=False;self.integrity='ok';self.issues.clear();self.pending_issues.clear();self.pending_time=None;self.fight_identity=None;self.fight_location={}
        self.actor_issues.clear();self.pending_actor_issues.clear()
    def invalidate(self,identifiers=None):
        # A retransmission may dispute an already closed frame. Revise only its
        # recorded consumers, never unrelated earlier fights.
        identifiers=set(identifiers) if identifiers is not None else {self.sequence+1}
        for fight in self.closed:
            if fight['id'] not in identifiers:continue
            fight['integrity']='conflicting_tcp';fight['partial']=True;fight['coverage_incomplete']=True
            fight['quality_issues']['conflicting_tcp']=fight['quality_issues'].get('conflicting_tcp',0)+1
            fight['total_damage']=None;fight['dps']=None
            fight['total_healing']=None;fight['hps']=None
            for section in fight.get('damage_sections',{}).values():
                section['total_damage']=None;section['dps']=None
                for actor in section['actors']:actor['dps']=None
            for actor in fight['actors']:actor['dps']=None;actor['hps']=None
        if self.active and self.sequence+1 in identifiers:
            self.integrity='conflicting_tcp';self.issue('conflicting_tcp');self.finish('transport_conflict')
    def summary(self,entries,reason,identifier):
        from ..healing import RECOVERY_EXCLUSIONS
        totals=Counter();healing=Counter();summoned=Counter();dots=Counter();hits=Counter();crits=Counter();targets=Counter();names={};classes={};sources={};timeline=Counter();skills=Counter();skill_healing=Counter();skill_hits=Counter();skill_crits=Counter();skill_dots=Counter();skill_summoned=Counter();dot_damage=Counter()
        damage_entries=[entry for entry in entries if entry.kind=='damage']
        damage_events=Counter(e.actor for e in entries if e.kind=='damage');heal_events=Counter(e.actor for e in entries if e.kind=='heal' and e.skill not in RECOVERY_EXCLUSIONS)
        start=damage_entries[0].time;last=damage_entries[-1].time
        seconds=max(1,(last-start)/1000)
        heal_self=Counter();heal_group=Counter();heal_other=Counter();heal_timeline=Counter();self_timeline=Counter();other_timeline=Counter();skill_self=Counter();skill_other=Counter();servers={e.actor:e.actor_server for e in entries}
        healing_seconds=max(1,(max(e.time for e in entries if e.kind=='damage' or e.skill not in RECOVERY_EXCLUSIONS)-start)/1000)
        recovery=Counter();recovery_events=0
        for entry in entries:
            key=(entry.actor,entry.skill)
            if entry.kind=='heal':
                if entry.skill in RECOVERY_EXCLUSIONS:
                    recovery[key]+=entry.damage;recovery_events+=1;continue
                healing[entry.actor]+=entry.damage;skill_healing[key]+=entry.damage
                names[entry.actor]=entry.name;classes[entry.actor]=entry.class_name;sources[entry.actor]=entry.name_source
                totals.setdefault(entry.actor,0)
                second=(entry.time-start)//1000;heal_timeline[second]+=entry.damage
                if entry.healing_scope=='self':
                    heal_self[entry.actor]+=entry.damage;skill_self[key]+=entry.damage;self_timeline[second]+=entry.damage
                else:
                    heal_other[entry.actor]+=entry.damage;skill_other[key]+=entry.damage;other_timeline[second]+=entry.damage
                    if entry.healing_scope=='group':heal_group[entry.actor]+=entry.damage
                continue
            skill_hits[key]+=0 if entry.periodic else entry.hits
            skill_crits[key]+=int(entry.critical);skill_dots[key]+=int(entry.periodic)
            if entry.periodic:dot_damage[entry.actor]+=entry.damage
            if entry.source_entity and entry.source_entity!=entry.actor:skill_summoned[key]+=entry.damage
            targets[entry.target]+=entry.damage
            if entry.critical:crits[entry.actor]+=1
            if not entry.periodic:hits[entry.actor]+=entry.hits
            if entry.periodic:dots[entry.actor]+=1
            if entry.source_entity and entry.source_entity!=entry.actor:summoned[entry.actor]+=entry.damage
            totals[entry.actor]+=entry.damage;names[entry.actor]=entry.name;classes[entry.actor]=entry.class_name;sources[entry.actor]=entry.name_source
            timeline[(entry.time-start)//1000]+=entry.damage;skills[(entry.actor,entry.skill)]+=entry.damage
        cast_counts=Counter();actor_casts=Counter();equipment=dict(self.actor_equipment)
        for event in self.cast_events:
            if event['key'] in self.cast_assigned or not start-1000<=event['time']<=last:continue
            actor=event['actor'];cast_counts[(actor,event['skill'])]+=1;actor_casts[actor]+=1
            if actor not in equipment and event.get('equipment'):equipment[actor]=event['equipment']
            if actor not in totals:
                totals[actor]=0;names[actor]=event['name'];classes[actor]=event['class'];sources[actor]=event['name_source']
        usage={}
        for (actor,skill),count in cast_counts.items():
            family=skill-skill%10000 if 11_000_000<=skill<20_000_000 else skill
            # Keep class Dodge separate from equip/basic-attack messages.
            if 11_000_000<=skill<20_000_000 and skill%1_000_000 in (100,101):family=skill-skill%100
            row=usage.setdefault((actor,family),{'actor':actor,'skill':family,'casts':0,'variants':[],'charges':{}})
            row['casts']+=count;row['variants'].append({'skill':skill,'casts':count})
            from .skill_labels import specialization_key
            if family==17060000 and specialization_key(skill) is not None and skill%10 in (1,2,3):row['charges'][str(skill%10)]=row['charges'].get(str(skill%10),0)+count
        valid=self.integrity=='ok';total=sum(totals.values())
        primary=targets.most_common(1)[0][0] if targets else None
        npc=self.world.npcs.get(primary)
        boss=next((self.world.npcs[t] for t,_ in targets.most_common() if t in self.world.npcs and self.world.npcs[t].is_boss),None)
        order=self.encounters.order(self.fight_location.get('map_id'),boss.template) if boss else None
        location=dict(self.fight_location)
        location['dungeon_name_source']=location.get('location_source','') if location.get('dungeon_name') else ''
        location['region_name_source']=location.get('location_source','') if location.get('region_name') else ''
        location['location_assignment']='map' if location.get('area_name') else 'unknown'
        location['dungeon_assignment']='map' if location.get('dungeon_name') else 'unknown'
        possible=self.encounters.locations_for(boss.template) if boss else ()
        candidates=sorted({item.dungeon_name for item in possible if item.kind=='dungeon'})
        if boss and not location.get('area_name'):
            inferred=self.encounters.location_for_boss(boss.template,location.get('map_id'))
            if inferred:
                location.update(area_name=inferred.area_name,area_kind=inferred.kind,location_assignment='boss_catalog')
                if inferred.kind=='dungeon':location.update(dungeon_name=inferred.area_name,dungeon_name_source=inferred.source,dungeon_assignment='boss_catalog')
                else:location.update(region_name=inferred.area_name,region_name_source=inferred.source)
        boss_type=('world_boss' if location.get('area_kind')=='field' else 'dungeon_boss' if location.get('area_kind')=='dungeon' else 'unknown') if boss else None
        target_kinds={entry.target_kind for entry in damage_entries}
        combat_type='mixed' if {'player','npc'}<=target_kinds else ('pvp' if 'player' in target_kinds else ('pve' if 'npc' in target_kinds else 'unknown'))
        group_state=self.fight_group_state
        if not self.world.party_trusted:group_state='invalid'
        # The reference meter documents this field-boss observation pattern:
        # many periodic-only actors but very few actors with direct-hit amounts.
        # This is a coverage warning, never an estimate of missing damage.
        with_hits=sum(amount>0 and hits[actor]>0 for actor,amount in totals.items())
        periodic_only=sum(amount>0 and hits[actor]==0 for actor,amount in totals.items())
        sparse=boss_type=='world_boss' and with_hits>0 and periodic_only>=5 and with_hits*4<=periodic_only
        # Our field-raid capture also contains tiny direct amounts for a few
        # allies. Flag the separate extreme-skew pattern conservatively: many
        # named actors with repeated actions, five without any damage amount,
        # and at least 95% of all observed damage from a single actor.
        active_cast_actors=[actor for actor,count in actor_casts.items() if count>=10]
        amountless=sum(totals[actor]==0 for actor in active_cast_actors)
        if boss_type=='world_boss' and len(active_cast_actors)>=10 and amountless>=5 and total>0 and max(totals.values())>=total*.95:sparse=True
        quality=dict(self.issues)
        if sparse:quality['worldboss_damage_sparse']=1
        from .damage_sections import damage_sections
        sections=damage_sections(entries,valid) if location.get('dungeon_name') else {}
        return {**location,'damage_sections':sections,'combat_type':combat_type,'id':identifier,'start_ms':start,'last_damage_ms':last,'seconds':seconds,'reason':reason,'integrity':self.integrity,
                'group_state':group_state,'group_coverage_confirmed':group_state in ('members','solo') if self.party_only else None,
                'damage_coverage':'sparse_worldboss_amounts' if sparse else 'observed_only',
                'partial':self.fight_partial or bool(quality),'coverage_incomplete':bool(quality),
                'connection_epoch':self.connection_epoch,'quality_issues':quality,'self_identity':dict(self.fight_identity or {}),
                'target_id':primary,'target_name':npc.name if npc else '',
                'target_template':npc.template if npc else 0,'target_hp':npc.hp if npc else None,'target_max_hp':npc.max_hp if npc else 0,
                'boss_id':boss.entity if boss else None,'boss_name':boss.name if boss else '',
                'boss_type':boss_type,'boss_template':boss.template if boss else None,'boss_name_source':boss.name_source if boss else '',
                'boss_area_candidates':[{'kind':kind,'name':name} for kind,name in sorted({(item.kind,item.area_name) for item in possible})],'boss_dungeon_candidates':candidates,'boss_index':order.index if order else None,'boss_order_source':order.source if order else '',
                'run_key':f"{self.connection_epoch}:{self.fight_location.get('zone_sequence')}" if self.fight_location.get('map_id') is not None else None,
                'targets':[{'id':target,'damage':amount,'template':self.world.npcs[target].template if target in self.world.npcs else None,'name':self.world.npcs[target].name if target in self.world.npcs else '', 'is_boss':self.world.npcs[target].is_boss if target in self.world.npcs else False} for target,amount in targets.most_common()],
                'total_damage':total if valid else None,'dps':total/seconds if valid else None,
                'healing_observed':True,'healing_seconds':healing_seconds,'total_healing':sum(healing.values()) if valid else None,'hps':sum(healing.values())/healing_seconds if valid else None,
                'healing_filtered':True,'healing_coverage_incomplete':bool(recovery_events),'unclassified_recovery_events':recovery_events,
                'healing_timeline':[{'second':second,'healing':amount,'self_healing':self_timeline[second],'other_healing':other_timeline[second]} for second,amount in sorted(heal_timeline.items())],
                'casts_observed':True,'cast_window_start_ms':start-1000,'cast_usage':list(usage.values()),'buffs':self.buffs.summary(start,last,set(totals)),'buffs_observed_only':True,
                'actors':[{'id':actor,'name':names[actor],'class':classes[actor],'server':servers.get(actor,0),'name_source':sources[actor],'damage':amount,'healing':healing[actor],'self_healing':heal_self[actor],'other_healing':heal_other[actor],'group_healing':heal_group[actor],'hps':healing[actor]/healing_seconds if valid else None,'summon_damage':summoned[actor],'dot_ticks':dots[actor],'dot_damage':dot_damage[actor],'hits':hits[actor],'crits':crits[actor],'dps':amount/seconds if valid else None,'casts':actor_casts[actor],'data_quality':{'damage_events':damage_events[actor],'healing_events':heal_events[actor],'casts':actor_casts[actor],'issues':{reason:count for (source,reason),count in self.actor_issues.items() if source==actor},'completeness_confirmed':False},**equipment.get(actor,{})} for actor,amount in totals.most_common()],
                'timeline':[{'second':second,'damage':amount} for second,amount in sorted(timeline.items())],
                'skills':[{'actor':actor,'skill':skill,'damage':skills[(actor,skill)],'healing':skill_healing[(actor,skill)],'unclassified_recovery':recovery[(actor,skill)],'self_healing':skill_self[(actor,skill)],'other_healing':skill_other[(actor,skill)],'hits':skill_hits[(actor,skill)],'crits':skill_crits[(actor,skill)],'dot_ticks':skill_dots[(actor,skill)],'summon_damage':skill_summoned[(actor,skill)],'casts':cast_counts[(actor,skill)]} for actor,skill in sorted(set(skills)|set(skill_healing)|set(cast_counts)|set(recovery))]}
    def snapshot(self):
        from copy import deepcopy
        return deepcopy(self.closed+([self.summary(self.active,'active',self.sequence+1)] if self.active else []))
