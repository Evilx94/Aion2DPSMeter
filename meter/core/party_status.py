"""Own-capture 1c/92 party status, joined only to full current player records.

The partial recovery is not a complete roster. Never infer actors from class,
position, damage targets or older connections. All quantities remain opaque.
"""
from dataclasses import dataclass
import math,struct
from .binary import Cursor,InvalidData

@dataclass(frozen=True)
class PartyStatus:
    character_id:int
    class_name:str
    context:bytes
    level:int
    gear:int
    power:int

    @property
    def map_id(self):return int.from_bytes(self.context[:4],'little')

def status_record(payload,raid=False):
    from .parser import wire_class
    if not (62 if raid else 63)<=len(payload)<=159:raise InvalidData('party status length')
    c=Cursor(payload);identifier=c.uint(8);server=identifier>>48
    if not 1000<=server<=9999 or not identifier&((1<<48)-1):raise InvalidData('party status character id')
    cls=wire_class(c.uint(4));context=c.take(12)
    # This is a u32 map ID, not a fixed low-byte marker. Own captures
    # corroborate 600071/600072 (Horn Den) and 600053 (Atiel area).
    # The other two u32 values remain opaque routing/context data.
    if not cls or not 1<=int.from_bytes(context[:4],'little')<=9999999:raise InvalidData('party status class/map')
    coords=struct.unpack('<fff',c.take(12))
    if any(not math.isfinite(v) or abs(v)>=10000000 for v in coords):raise InvalidData('party status coordinates')
    level=c.uint(4);c.take(4);gear=c.uint(4);length=c.uint(1)
    if length>96 or not 1<=level<=200 or not 0<=gear<=50000:raise InvalidData('party status metadata')
    try:guild=c.take(length).decode('utf-8')
    except UnicodeError as error:raise InvalidData('party status guild UTF8') from error
    if any(not char.isprintable() for char in guild):raise InvalidData('party status guild text')
    c.take(4)
    if not raid and c.uint(1)!=1:raise InvalidData('party status metadata marker')
    power=c.uint(8)
    # Same structured status: trailers 02 (08:05) and 03 (08:25/08:29),
    # corroborated by full rosters with matching class/level/gear/power.
    # The trailer meaning remains opaque; it is not an identity or group key.
    if power>10000000 or c.uint(1) not in (1,2,3) or c.remaining:raise InvalidData('party status tail')
    return PartyStatus(identifier,cls,context,level,gear,power)

class StatusRecovery:
    TTL=15000
    def __init__(self):self.generation=None;self.rows={};self.signature=None
    def sync(self,world,time):
        if self.generation!=world.generation:
            self.generation=world.generation;self.rows.clear();self.signature=None
        if time is None:return False
        previous=len(self.rows)
        self.rows={key:value for key,value in self.rows.items() if 0<=time-value[2]<=self.TTL}
        return len(self.rows)!=previous
    def observe(self,world,record,time):
        self.sync(world,time)
        if time is None:return
        old=self.rows.get(record.character_id)
        if old and time<=old[2]:return
        agreeing=old and old[0].class_name==record.class_name
        count=min(2,old[1]+1) if agreeing else 1
        if len(self.rows)>=20 and record.character_id not in self.rows:return
        self.rows[record.character_id]=(record,count,time)
    def refresh(self,world,time):
        self.sync(world,time)
        # Fresh explicit social state always wins. Invalid explicit rosters do
        # not get bypassed by this recovery, even if old statuses still exist.
        if not world.party_trusted or (world.party_known and world.party_source!='status_recovery'):return
        if world.self_entity is None or world.self_recognition not in ('self_info','local_updates') or world.local_conflict:return
        confirmed=[r for r,count,stamp in self.rows.values() if count>=2]
        matches={};identifiers_by_actor={}
        for record in confirmed:
            encoded=record.character_id.to_bytes(8,'little');server=record.character_id>>48
            for entity,payload in world.player_records.items():
                person=world.people.get(entity)
                if not person or not person.confirmed or not person.name or person.class_name!=record.class_name or person.server not in (0,server):continue
                if payload.count(encoded)==1:
                    matches.setdefault(record.character_id,[]).append(person)
                    identifiers_by_actor.setdefault(entity,set()).add(record.character_id)
        members=[]
        for record in confirmed:
            candidates=matches.get(record.character_id,[])
            if len(candidates)!=1 or len(identifiers_by_actor[candidates[0].entity])!=1:continue
            person=candidates[0]
            members.append({'name':person.name,'server':record.character_id>>48,'class':record.class_name,'character_id':record.character_id,'level':record.level,'gear':record.gear,'power':record.power,'membership_source':'server_party_status'})
        signature=tuple(sorted(tuple(sorted(r.items())) for r in members))
        if signature==self.signature:return
        self.signature=signature
        if members or world.party_source=='status_recovery':world.party(members,complete=False,source='status_recovery')


class RaidStatusRecovery(StatusRecovery):
    """Fresh 2b96/2c96 raid statuses can extend a proven local subgroup partially.

    No prior recording or pre-gap membership is used. Require two fresh status
    timestamps and an exact full-player character-ID match, or a confirmed named
    player on the explicit live raid-status entity. Require a current subgroup. Expiring evidence only
    removes rows added by this recovery, never explicit social snapshot rows.
    """
    def __init__(self):super().__init__();self.anchor=None;self.actor_rows={}
    def sync(self,world,time):
        changed=self.generation!=world.generation
        expired=super().sync(world,time)
        if changed:self.actor_rows.clear()
        if time is not None:
            previous=len(self.actor_rows)
            self.actor_rows={entity:value for entity,value in self.actor_rows.items() if 0<=time-value[1]<=self.TTL and value[2]==world.identity_token(entity)}
            expired=expired or len(self.actor_rows)!=previous
        return expired
    def observe_actor(self,world,entity,time):
        self.sync(world,time)
        if self.anchor!=world.party_key:
            self.rows.clear();self.actor_rows.clear();self.anchor=world.party_key
        if time is None:return
        old=self.actor_rows.get(entity)
        if old and time<=old[1]:return
        if len(self.actor_rows)>=20 and entity not in self.actor_rows:return
        self.actor_rows[entity]=(min(2,old[0]+1) if old else 1,time,world.identity_token(entity))
    def refresh(self,world,time):
        self.sync(world,time)
        if self.anchor!=world.party_key:
            self.rows.clear();self.actor_rows.clear();self.anchor=world.party_key
        if not world.party_trusted or not world.party_known or world.party_source=='server_leave':return
        if world.self_entity is None or world.self_recognition not in ('self_info','local_updates') or world.local_conflict:return
        base=[dict(r) for r in world.party_records if r.get('membership_source') not in ('raid_status_recovery','raid_actor_status')]
        if not base or len(base)>20:return
        signature=(world.generation,world.party_key,world.self_entity,tuple((entity,count,tuple(token),world.people.get(entity),entity in world.retired,entity in world.npcs,entity in world.summons) for entity,(count,stamp,token) in self.actor_rows.items()),tuple((cid,r.class_name,count>=2,r.level,r.gear,r.power) for cid,(r,count,stamp) in self.rows.items()),tuple((entity,id(payload)) for entity,payload in world.player_records.items()),tuple((r.get('character_id'),r['name'],r['server'],r.get('class'),r.get('membership_source')) for r in world.party_records))
        if signature==self.signature:return
        self.signature=signature
        additions=[];used=set()
        for record,count,stamp in self.rows.values():
            if count<2:continue
            if any(r.get('character_id')==record.character_id for r in base):continue
            encoded=record.character_id.to_bytes(8,'little');server=record.character_id>>48
            candidates=[]
            for entity,payload in world.player_records.items():
                person=world.people.get(entity)
                if person and person.confirmed and person.name and person.class_name==record.class_name and person.server in (0,server) and payload.count(encoded)==1:
                    candidates.append(person)
            if len(candidates)!=1:continue
            person=candidates[0]
            # An entity appearing under two character IDs is ambiguous.
            if sum(payload.count(other.character_id.to_bytes(8,'little'))==1 for other,_,_ in self.rows.values() for entity,payload in world.player_records.items() if entity==person.entity)!=1:continue
            key=(person.name,server)
            if person.entity in used or any((r['name'],r['server'])==key for r in base+additions):continue
            used.add(person.entity)
            additions.append({'name':person.name,'server':server,'class':record.class_name,'character_id':record.character_id,'level':record.level,'gear':record.gear,'power':record.power,'membership_source':'raid_status_recovery'})
        for entity,(count,stamp,token) in self.actor_rows.items():
            if count<2 or token!=world.identity_token(entity) or entity in world.retired or entity in world.npcs or entity in world.summons:continue
            person=world.people.get(entity)
            if not person or not person.confirmed or not person.name or not person.class_name:continue
            server=world.player_server(entity)
            if any((r['name'],r['server'])==(person.name,server) for r in base+additions):continue
            if entity in used:continue
            used.add(entity)
            additions.append({'name':person.name,'server':server,'class':person.class_name,'membership_source':'raid_actor_status','evidence_entity':entity,'evidence_token':list(token)})
        if len(base)+len(additions)>20:return
        members=tuple(base+additions)
        if members==world.party_records:return
        had_recovery=world.party_source=='raid_status_recovery'
        if additions or had_recovery:
            world.party(members,party_key=world.party_key,complete=False,source='raid_status_recovery' if additions else 'snapshot')
    def observe(self,world,record,time):
        self.sync(world,time)
        if self.anchor!=world.party_key:
            self.rows.clear();self.actor_rows.clear();self.anchor=world.party_key
        super().observe(world,record,time)


def raid_actor_status(payload):
    """2b96 live raid-member status, bounded from 669 complete own records.

    HP and resource counters validate the envelope only; differences are never
    damage. The 17-byte remainder is opaque except its observed terminal 01.
    """
    from .damage import checked_entity
    c=Cursor(payload);entity=checked_entity(c);current=c.variable();maximum=c.variable()
    if not 0<=current<=maximum<=10000000000 or maximum==0 or c.remaining!=25:
        raise InvalidData('raid actor status health/length')
    resource=c.uint(4);limit=c.uint(4);tail=c.take(17)
    if resource>limit or tail[-1]!=1:raise InvalidData('raid actor status tail')
    return entity
