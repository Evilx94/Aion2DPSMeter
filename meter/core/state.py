"""Event-time group authorization, explicit owners and immutable identities."""
from dataclasses import dataclass
@dataclass(frozen=True)
class Person:
    entity:int
    name:str=''
    server:int=0
    confirmed:bool=False
    class_name:str=''
    name_source:str=''
@dataclass
class Npc:
    entity:int
    hp:int|None=None
    max_hp:int=0
    spawn_hp_candidate:int=0
    position:tuple=()
    alive:bool|None=None
    in_combat:bool|None=None
    name:str=''
    origin:str='hp'
    template:int=0
    is_boss:bool=False
    name_source:str=''
    updated_ms:int|None=None
class World:
    def __init__(self,preferred_identity=None):
        self.preferred_identity={};self.set_preferred_identity(preferred_identity);self.reset()
    def set_preferred_identity(self,profile):
        # A remembered name is a lookup key, never a remembered entity number.
        if not isinstance(profile,dict):return
        name=profile.get('name');server=profile.get('server')
        if isinstance(name,str) and name and len(name)<=16 and name.isalnum() and any(c.isalpha() for c in name) and type(server) is int and 1<=server<=9999:
            self.preferred_identity={'name':name,'server':server}
    def reset(self):
        self.party_complete=True
        self.people={};self.owners={};self.summons={};self.npcs={};self.retired=set();self.unresolved_damage=set();self.members=frozenset();self.party_records=();self.player_records={};self.party_links={};self.party_trusted=True;self.party_known=False;self.party_key=None;self.entity_versions={};self.self_entity=None;self.self_recognition='';self.local_candidates={};self.local_conflict=False;self.generation=getattr(self,'generation',-1)+1
    def local_identity(self,entity,time):
        if time is None:return False
        if entity in self.summons or (entity in self.npcs and self.npcs[entity].origin=='spawn'):return False
        # Require distinct messages, not duplicates replayed with the same time.
        previous=self.local_candidates.get(entity)
        if previous and time<=previous[1]:return False
        count=(previous[0]+1) if previous and time-previous[1]<=10000 else 1
        if len(self.local_candidates)>=8 and entity not in self.local_candidates:self.local_conflict=True;return False
        self.local_candidates[entity]=(count,time)
        if count<2:return False
        if self.self_entity is not None and self.self_entity!=entity and self.self_recognition in ('self_info','local_updates'):
            self.local_conflict=True
            if self.self_recognition=='local_updates':self.self_entity=None;self.self_recognition=''
            return False
        if self.local_conflict:return False
        self.npcs.pop(entity,None);self.retired.discard(entity);self.observe(entity)
        self.self_entity=entity
        if self.self_recognition!='self_info':self.self_recognition='local_updates'
        self.learn_local_name();self.bind_summons();return True
    def learn_local_name(self):
        person=self.people.get(self.self_entity)
        if person is None:return
        # Typed named-owner records carry both the owner's exact ID and name.
        # Name-only inline records do not prove which player is local.
        names={r.name for r in self.summons.values() if r.evidence=='named_owner' and r.owner==self.self_entity and r.name}
        if not person.name and len(names)==1:
            self.identity(person.entity,next(iter(names)),person.server,confirmed=True,class_name=person.class_name)
    def zone_reset(self):
        records=self.party_records;trusted=self.party_trusted;known=self.party_known;key=self.party_key;complete=self.party_complete
        self.reset();self.party(records,party_key=key,complete=complete);self.party_trusted=trusted;self.party_known=known
    def player_record(self,entity,payload):
        if len(payload)>8192:return
        if len(self.player_records)>=2048 and entity not in self.player_records:self.player_records.pop(next(iter(self.player_records)))
        self.player_records[entity]=bytes(payload);self.link_party();self.bind_summons()
    def link_party(self):
        from collections import defaultdict
        self.party_links={}
        if not self.party_trusted:return
        candidates=defaultdict(list);identifiers_by_actor=defaultdict(set)
        for member in self.party_records:
            identifier=member.get('character_id',0);server=member.get('server',0);cls=member.get('class','')
            if type(identifier) is not int or not 0<identifier<2**64 or identifier>>48!=server or not identifier&((1<<48)-1) or not cls:continue
            encoded=identifier.to_bytes(8,'little')
            for entity,payload in self.player_records.items():
                person=self.people.get(entity)
                if not person or not person.confirmed or person.name!=member['name'] or person.class_name!=cls or person.server not in (0,server):continue
                # Complete, unique character-ID match inside a validated player
                # record, plus matching server roster name and class.
                if payload.count(encoded)==1:candidates[identifier].append(entity);identifiers_by_actor[entity].add(identifier)
        for member in self.party_records:
            identifier=member.get('character_id',0);actors=candidates.get(identifier,())
            if len(actors)==1 and len(identifiers_by_actor[actors[0]])==1:self.party_links[actors[0]]=(member['name'],member['server'],identifier)
    def player_server(self,entity):
        person=self.people.get(entity)
        if person and person.server:return person.server
        link=self.party_links.get(entity)
        return link[1] if link and self.party_trusted else 0
    def identity(self,entity,name,server=0,own=False,confirmed=True,class_name='',name_source='server'):
        self.forget_summon(entity);self.npcs.pop(entity,None);self.retired.discard(entity)
        previous=self.people.get(entity)
        if previous and ((previous.name and previous.name.casefold()!=name.casefold()) or (previous.server and server and previous.server!=server)):
            self.entity_versions[entity]=self.entity_versions.get(entity,0)+1
        if previous and previous.name.casefold()==name.casefold() and (previous.server==server or not previous.server) and not class_name:class_name=previous.class_name
        self.people[entity]=Person(entity,name,server,confirmed,class_name,name_source)
        if own:
            self.local_conflict=False;self.local_candidates.clear()
            self.self_entity=entity;self.self_recognition='self_info' if confirmed and name_source=='server' else 'manual'
            if confirmed and server:self.set_preferred_identity({'name':name,'server':server})
        elif entity==self.self_entity and previous:
            if (previous.name and previous.name.casefold()!=name.casefold()) or (previous.server and server and previous.server!=server):
                self.self_entity=None;self.self_recognition=''
            elif confirmed and server:
                self.set_preferred_identity({'name':name,'server':server})
        self.player_records.pop(entity,None);self.link_party();self.bind_summons()
    def observe(self,entity,class_name=''):
        if entity in self.summons:return
        npc=self.npcs.get(entity)
        if npc:
            if npc.origin=='spawn' or not class_name:return
            self.npcs.pop(entity,None);self.retired.discard(entity)
        if entity in self.retired and entity not in self.people:return
        changed=False
        if entity not in self.people:self.people[entity]=Person(entity,class_name=class_name);changed=True
        elif class_name and not self.people[entity].class_name:
            from dataclasses import replace
            self.people[entity]=replace(self.people[entity],class_name=class_name);changed=True
        if changed:self.bind_summons()
    def npc(self,entity):
        if entity in self.people or entity in self.summons:return None
        if len(self.npcs)>=10000 and entity not in self.npcs:
            self.npcs.pop(next(iter(self.npcs)))
        return self.npcs.setdefault(entity,Npc(entity))
    def identity_token(self,entity):
        return [self.generation,self.entity_versions.get(entity,0)]
    def respawn(self,entity):
        self.entity_versions[entity]=self.entity_versions.get(entity,0)+1
        self.forget_summon(entity);self.npcs.pop(entity,None);self.retired.discard(entity);self.player_records.pop(entity,None);self.party_links.pop(entity,None)
        self.unresolved_damage.discard(entity)
    def retire(self,entity):
        npc=self.npcs.get(entity)
        if npc:npc.alive=False;npc.hp=0
        self.forget_summon(entity);self.retired.add(entity);self.unresolved_damage.discard(entity)
        if len(self.retired)>10000:self.retired.pop()
    def forget_summon(self,entity):
        self.summons.pop(entity,None);self.owners.pop(entity,None)
    def summon(self,record):
        self.forget_summon(record.entity)
        person=self.people.get(record.entity)
        if person and person.confirmed:return False
        if self.self_entity==record.entity:self.self_entity=None
        self.people.pop(record.entity,None);self.npcs.pop(record.entity,None);self.retired.discard(record.entity)
        if len(self.summons)>=2048:
            self.forget_summon(next(iter(self.summons)))
        self.summons[record.entity]=record
        self.learn_local_name();self.bind_summons()
        return record.entity in self.owners
    def bind_summons(self):
        from collections import deque,defaultdict
        # Recompute at identity changes so stale names/servers revoke bindings.
        dependencies=defaultdict(list)
        for entity,record in self.summons.items():
            self.owners.pop(entity,None)
            if record.owner:dependencies[record.owner].append(entity)
        queue=deque(self.summons);scheduled=set(queue);bound=set()
        while queue:
            entity=queue.popleft();scheduled.discard(entity)
            if entity in bound:continue
            record=self.summons[entity];owner=record.owner
            if record.evidence=='inline_name':
                candidates=[p.entity for p in self.people.values() if p.entity!=entity and p.name==record.name and (p.confirmed or p.entity==self.self_entity)]
                if len(candidates)!=1:continue
                owner=candidates[0]
            root=self.resolve(owner);person=self.people.get(root)
            if not person:continue
            own=root==self.self_entity;server=self.player_server(root)
            matched=((record.evidence=='inline_name') or
                     (record.evidence=='named_owner' and person.name==record.name and (person.confirmed or own)) or
                     (record.evidence=='parent_server' and ((person.confirmed and server==record.server) or (own and server in (0,record.server)))) or
                     (record.evidence=='paired_parent' and (person.confirmed or own or bool(person.class_name)) and (record.server==0 or server in (0,record.server))))
            if not matched:continue
            try:self.owner(entity,owner)
            except ValueError:continue
            bound.add(entity);self.unresolved_damage.discard(entity)
            for child in dependencies[entity]:
                if child not in scheduled and child not in bound:queue.append(child);scheduled.add(child)
    def party(self,members,party_key=None,complete=True):
        self.party_key=party_key
        self.party_complete=bool(complete)
        self.party_records=tuple(dict(m) for m in members)
        self.members=frozenset((m['name'],m['server']) for m in self.party_records);self.party_trusted=True;self.party_known=True;self.link_party();self.bind_summons()
    def owner(self,pet,player):
        if pet==player:raise ValueError('self owner')
        previous=self.owners.get(pet);self.owners[pet]=player
        if self.resolve(pet) is None:
            if previous is None:self.owners.pop(pet)
            else:self.owners[pet]=previous
            raise ValueError('owner cycle')
    def resolve(self,entity):
        visited=set()
        while entity in self.owners:
            if entity in visited:return None
            visited.add(entity);entity=self.owners[entity]
        return entity
    def authorized(self,entity):
        if entity in self.retired and entity not in self.people:return False
        actor=self.resolve(entity)
        if actor is None:return False
        if actor==self.self_entity:return True
        person=self.people.get(actor)
        return bool(self.party_trusted and person and person.confirmed and ((person.name,person.server) in self.members or (actor in self.party_links and self.party_links[actor][:2] in self.members)))
