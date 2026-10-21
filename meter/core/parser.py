"""Candidate metadata parsing; no scans of arbitrary bodies for embedded records."""
from .binary import Cursor,InvalidData
from .damage import damage_message,periodic_message

def wire_class(value):
    ranges=[(5,8,'Gladiator'),(9,12,'Templar'),(13,16,'Ranger'),(17,20,'Assassin'),(21,24,'Elementalist'),(25,28,'Sorcerer'),(29,32,'Cleric'),(33,36,'Chanter'),(45,48,'Brawler')]
    return next((name for low,high,name in ranges if low<=value<=high),'')

def text(cursor,length):
    try:value=cursor.take(length).decode('utf-8')
    except UnicodeError as error:raise InvalidData('invalid UTF8') from error
    if not value or len(value)>16 or not value.isalnum() or not any(c.isalpha() for c in value):raise InvalidData('invalid character name')
    return value

def roster_header(payload):
    c=Cursor(payload);key=c.uint(4);length=c.uint(1)
    if length>64:raise InvalidData('group name length')
    c.take(length);size=c.uint(1)
    if not 0<=size<=20:raise InvalidData('group size')
    c.take(17);count=c.variable()
    if not 0<=count<=size:raise InvalidData('unconfirmed member count')
    return key,size,count,c.position


def roster(payload):
    key,size,count,start=roster_header(payload)
    if size==0 and count==0 and start==len(payload):return ()
    if count==0:raise InvalidData('unconfirmed member count')
    if len(payload)>16384:raise InvalidData('group body limit')
    def member(at):
        c=Cursor(payload,at);mask=c.uint(1);slot=c.uint(1);identifier=c.uint(8)
        if slot>20:raise InvalidData('group slot range')
        if mask==0 and identifier==0:
            # Re-entering Horn Den after a member left: the captured vacant
            # record is 37 bytes, with status 01 at byte 24 (other fields zero).
            if at+37<=len(payload) and payload[at+24]==1:
                newer=bytearray(37);newer[1]=slot;newer[24]=payload[at+24]
                if payload[at:at+37]==bytes(newer):
                    return {'slot':slot,'vacant':True,'character_id':0},at+37
            # Exact observed vacant-slot record: 35 bytes, byte 23 is 01..04;
            # all remaining fields zero. This removes the slot, not membership
            # inferred from older rosters. Unknown empty forms are not guessed.
            if at+35>len(payload) or payload[at+23] not in (1,2,3,4):raise InvalidData('unconfirmed vacant group slot')
            expected=bytearray(35);expected[1]=slot;expected[23]=payload[at+23]
            if payload[at:at+35]!=bytes(expected):raise InvalidData('unconfirmed vacant group slot')
            return {'slot':slot,'vacant':True,'character_id':0},at+35
        server=identifier>>48;name=text(c,c.uint(1))
        if not 1<=server<=9999:raise InvalidData('server range')
        class_id=c.uint(4);level=c.uint(4);gear=c.uint(4)
        if not wire_class(class_id) or not 1<=level<=200:raise InvalidData('group class/level')
        if mask&1 and gear<100:
            extension=Cursor(payload,c.position);possible=extension.uint(4)
            if 100<=possible<=50000:gear=possible;c.position=extension.position
        if not 0<=gear<=50000:raise InvalidData('group gear range')
        anchors=[i for i in range(c.position,min(len(payload)-13,c.position+10)+1)
                 if int.from_bytes(payload[i:i+2],'little')==server
                 and int.from_bytes(payload[i+2:i+4],'little')<=9999
                 and payload[i+4]<=4
                 and int.from_bytes(payload[i+5:i+13],'little')<=10000000]
        # Observed new member on re-entry: optional 03 | routing u16 pair |
        # status 01..04 | power u64. Routing values can differ from the character-ID server;
        # retain the character ID/server instead of guessing an alias mapping.
        if not anchors:
            # Repeated Fire Temple snapshots carry prefixes 02,06,07 before
            # the routing pair; prior re-entry captures carry 03 or no prefix.
            # Test only those exact positions and still require a unique full
            # routing/status/power structure, retaining the character-ID server.
            starts=[c.position]
            if payload[c.position:c.position+1] in (b'\x02',b'\x03',b'\x06',b'\x07'):starts.append(c.position+1)
            anchors=[at for at in starts if at+13<=len(payload)
                     and all(1000<=int.from_bytes(payload[i:i+2],'little')<=9999 for i in (at,at+2))
                     and payload[at+4] in (1,2,3,4)
                     and int.from_bytes(payload[at+5:at+13],'little')<=10000000]
        if len(anchors)!=1:raise InvalidData('ambiguous power anchor')
        c.position=anchors[0]+5;power=c.uint(8)
        if power>10000000:raise InvalidData('power range')
        return {'name':name,'server':server,'class_id':class_id,'class':wire_class(class_id),
                'character_id':identifier,'level':level,'gear':gear,'power':power,'slot':slot},c.position
    # Post-power status/position data is opaque; vacant slots must be counted
    # before parsing later named members. Require a unique complete bounded parse.
    first,end=member(start);paths=[([first],end)];work=0
    for _ in range(1,count):
        options=[]
        for rows,end in paths:
            for at in range(end,min(end+32,len(payload)-11)+1):
                if payload[at+1]!=rows[-1]['slot']+1:continue
                try:record,new_end=member(at)
                except InvalidData:continue
                if record['character_id']&((1<<48)-1) and record['character_id'] in {r['character_id'] for r in rows}:continue
                options.append((rows+[record],new_end));work+=1
                if work>256:raise InvalidData('ambiguous next member')
        paths=options
        if not paths:raise InvalidData('ambiguous next member')
    if len(paths)!=1:raise InvalidData('ambiguous next member')
    rows,end=paths[0]
    if len(payload)-end>512:raise InvalidData('group tail limit')
    return tuple(rows)


class Parser:
    def __init__(self,ledger,skill_policy=None,npc_policy=None):
        from .npc_policy import NpcPolicy
        self.npc_policy=npc_policy if npc_policy is not None else NpcPolicy.builtin()
        from .skill_policy import SkillPolicy
        self.skill_policy=skill_policy if skill_policy is not None else SkillPolicy.builtin()
        from collections import Counter
        self.ledger=ledger;self.counts=Counter();self.decisions=Counter();self.errors=Counter();self.map_id=None;self.map_token=None;self.zone_sequence=0
        self.login_membership=None;self.deferred_login=None
    def reset_location(self):
        self.map_id=None;self.map_token=None;self.ledger.set_location(None)
    def login_identity(self,rows,time):
        """Bind names only to a freshly proven local entity, never a roster guess."""
        world=self.ledger.world;own=world.people.get(world.self_entity)
        if own is None:return own
        candidate=world.local_candidates.get(world.self_entity)
        local_proof=(world.self_recognition=='local_updates' and not world.local_conflict and candidate is not None and candidate[0]>=2 and time is not None and 0<=time-candidate[1]<=10000)
        if not local_proof and not (world.self_recognition=='self_info' and own.confirmed):return own
        matches=[r for r in rows if r['id'] and r['id']==own.entity
                 and (not own.name or r['name']==own.name)
                 and (not own.server or r['server']==own.server)
                 and (not own.class_name or r['class']==own.class_name)]
        if len(matches)!=1:return own
        row=matches[0]
        if not own.confirmed or not own.name or not own.server or not own.class_name:
            world.identity(own.entity,row['name'],row['server'],class_name=row['class'])
            self.ledger.identified_self(time);self.ledger.refresh_identity(own.entity)
            self.decisions['login_group:local_entity_name_bound']+=1
        return world.people.get(world.self_entity)

    def accept(self,message,time=None):
        op=message.opcode;body=message.body;world=self.ledger.world
        deferred=self.deferred_login
        if deferred:
            pending,stamp,generation=deferred
            if generation!=world.generation or time is None or stamp is None or not 0<=time-stamp<=15000:
                self.deferred_login=None
            elif op not in (bytes.fromhex('0092'),bytes.fromhex('0296'),bytes([2,151])):
                own=world.people.get(world.self_entity)
                candidate=world.local_candidates.get(world.self_entity)
                if own and (own.confirmed or (world.self_recognition=='local_updates' and candidate and candidate[0]>=2 and 0<=time-candidate[1]<=10000)):
                    self.deferred_login=None
                    self.accept(pending,time)
        self.counts[op.hex(' ')]+=1
        try:
            if op in (bytes.fromhex('0092'),bytes.fromhex('0296'),bytes.fromhex('0d92'),bytes.fromhex('0a96')):
                from .login_group import snapshot,update,LoginMembership,PartialOwnGroup
                if self.login_membership and self.login_membership.generation!=world.generation:self.login_membership=None
                if op in (bytes.fromhex('0092'),bytes.fromhex('0296')):
                    self.deferred_login=None
                    record=snapshot(op,body)
                    own=self.login_identity(record.rows,time)
                    previous_ids={r['character_id'] for r in world.party_records if r.get('id')==world.self_entity}
                    if not own or not own.confirmed or not any((r['id']==own.entity or (r['id']==0 and r['character_id'] in previous_ids)) and r['name']==own.name and r['server']==own.server and r['class']==own.class_name for r in record.rows):
                        # Retain one structurally validated snapshot briefly; never
                        # authorize it before a fresh matching local identity exists.
                        if not own or not own.confirmed:self.deferred_login=(message,time,world.generation)
                        raise InvalidData('login roster missing local proof')
                    if record.raid:
                        from dataclasses import replace
                        own_row=next(r for r in record.rows if (r['id']==own.entity or (r['id']==0 and r['character_id'] in previous_ids)) and r['name']==own.name and r['server']==own.server and r['class']==own.class_name)
                        # Unkeyed party updates belong to the local player's
                        # subgroup, which need not be serialized first.
                        record=replace(record,own_group=own_row['login_group_key'])
                    self.login_membership=LoginMembership(record,world.generation)
                else:
                    key,row=update(op,body)
                    if not self.login_membership:
                        own=self.login_identity((row,),time) if op==bytes.fromhex('0d92') else world.people.get(world.self_entity)
                        if op!=bytes.fromhex('0d92') or not own or not own.confirmed or not (row['id']==own.entity and row['name']==own.name and row['server']==own.server and row['class']==own.class_name):
                            self.decisions['login_group:update_without_snapshot']+=1;return None
                        self.login_membership=PartialOwnGroup(row,world.generation)
                        self.decisions['login_group:recovered_own_update']+=1
                    elif isinstance(self.login_membership,PartialOwnGroup) and key is not None:
                        self.decisions['login_group:keyed_update_without_snapshot']+=1;return None
                    else:
                        pending=self.login_membership
                        if key is not None and not pending.snapshot.raid and key!=pending.snapshot.key:
                            # A bounded update for another subgroup is not a roster
                            # for ours. Preserve the verified party, but never add
                            # that player or infer a raid from the update alone.
                            overlaps=any(row['character_id']==r['character_id'] or (row['id'] and row['id']==r['id']) for r in pending.rows.values())
                            if not overlaps and key>>32==pending.snapshot.key>>32:
                                self.decisions['login_group:unrelated_subgroup_update']+=1;return None
                        pending.add(key,row)
                    record=row
                pending=self.login_membership
                members=tuple(pending.rows.values())
                for row in members:
                    if row['id']==0:continue
                    world.identity(row['id'],row['name'],row['server'],class_name=row['class'])
                    self.ledger.refresh_identity(row['id'])
                world.party(members,party_key=pending.snapshot.key,complete=pending.complete())
                self.decisions['login_group:complete' if pending.complete() else 'login_group:pending']+=1
                if self.ledger.active and not pending.complete():self.ledger.fight_group_state='partial'
                return record
            if op==bytes([74,54]):
                from .local_identity import local_update
                update=local_update(body)
                previous=world.self_entity
                bound=world.local_identity(update.entity,time)
                if previous is not None and previous!=world.self_entity:
                    self.ledger.issue('local_identity_changed',time=time);self.ledger.finish('local_identity_changed')
                if bound:self.ledger.identified_self(time);self.ledger.refresh_identity(world.self_entity)
                self.decisions['local:recognized' if bound else 'local:pending']+=1
                return update
            if op==bytes([2,56]):
                from .damage import checked_entity
                from .activity import cast_record
                # Legacy short headers still identify class, but cannot count a cast.
                cursor=Cursor(body);actor=checked_entity(cursor);cursor.variable();skill=cursor.uint(4)
                if not 1<=skill<=299999999:raise InvalidData('cast skill range')
                classes={11:'Gladiator',12:'Templar',13:'Assassin',14:'Ranger',15:'Sorcerer',16:'Elementalist',17:'Cleric',18:'Chanter',19:'Brawler'}
                if skill//1000000 in classes:world.observe(actor,classes[skill//1000000])
                if not cursor.remaining:
                    self.decisions['cast:metadata_only']+=1;return actor,skill
                record=cast_record(body)
                if time is not None:self.ledger.cast(time,record)
                self.decisions['cast:observed']+=1;return record
            if op in (bytes.fromhex('2a38'),bytes.fromhex('2b38'),bytes.fromhex('2c38')):
                from .activity import buff_record
                record=buff_record(op,body)
                if time is not None:self.ledger.buff(time,record)
                self.decisions['buff:'+record.operation]+=1;return record
            if op==bytes([4,56]):
                decision=damage_message(body);self.decisions[decision.status+':'+decision.reason]+=1
                if decision.status=='rejected':
                    # Decode only the independently bounded header for relevance.
                    try:
                        from .damage import checked_entity
                        probe=Cursor(body);target=checked_entity(probe);control=probe.variable();probe.variable();source=checked_entity(probe)
                        if target!=source and (target not in world.people or (self.ledger.track_pvp and not world.authorized(target))):self.ledger.issue('damage_parser:'+decision.reason,source,time)
                    except InvalidData:
                        if self.ledger.active:self.ledger.issue('damage_scope_unknown',time=time)
                for hit in decision.hits:
                    classes={11:'Gladiator',12:'Templar',13:'Assassin',14:'Ranger',15:'Sorcerer',16:'Elementalist',17:'Cleric',18:'Chanter',19:'Brawler'}
                    if hit.skill//1000000 in classes:world.observe(hit.source,classes[hit.skill//1000000])
                    if time is not None:self.ledger.accept(time,hit)
                return decision
            if op==bytes([2,151]):
                self.deferred_login=None
                slots=roster(body);key,size,count,_=roster_header(body)
                if count!=size:raise InvalidData('unconfirmed partial roster')
                members=tuple(row for row in slots if not row.get('vacant'))
                world.party(members,party_key=key)
                self.login_membership=None
                return members
            if op in (bytes([51,54]),bytes([69,54]),bytes([68,54])):
                from .damage import checked_entity
                cursor=Cursor(body);entity=checked_entity(cursor);cursor.take(4);mask=cursor.uint(1)
                if not mask&1:return
                name=text(cursor,cursor.uint(1));server=0;class_name=''
                own=op==bytes([51,54])
                if own:
                    if 0<cursor.remaining<6:raise InvalidData('truncated identity metadata')
                    if cursor.remaining>=6:
                        server=cursor.uint(2);class_name=wire_class(cursor.uint(4))
                        if not 1<=server<=9999 or not class_name:raise InvalidData('identity server/class range')
                elif cursor.remaining:
                    # Own captures contain both server+class and class-only
                    # player records. Validate the class instead of interpreting
                    # its low two bytes as a server number.
                    metadata=cursor.position;choices=[]
                    if cursor.remaining>=6:
                        srv=int.from_bytes(body[metadata:metadata+2],'little')
                        cls=wire_class(int.from_bytes(body[metadata+2:metadata+6],'little'))
                        if 1<=srv<=9999 and cls:choices.append((srv,cls))
                    if cursor.remaining>=4:
                        cls=wire_class(int.from_bytes(body[metadata:metadata+4],'little'))
                        if cls:choices.append((0,cls))
                    if len(choices)!=1:raise InvalidData('unconfirmed player identity metadata')
                    server,class_name=choices[0]
                if not own and server==0:
                    known=world.people.get(entity)
                    if known and known.confirmed and known.name.casefold()==name.casefold():server=known.server
                previous=world.people.get(world.self_entity)
                if own and previous and (previous.entity!=entity or (previous.name and previous.name.casefold()!=name.casefold()) or (previous.server and server and previous.server!=server)):
                    self.ledger.finish('character_change');world.reset();self.reset_location()
                elif entity==world.self_entity and previous and ((previous.name and previous.name.casefold()!=name.casefold()) or (previous.server and server and previous.server!=server)):
                    self.ledger.finish('identity_changed');world.reset();self.reset_location()
                world.identity(entity,name,server,op==bytes([51,54]),class_name=class_name)
                if not own:world.player_record(entity,body)
                self.ledger.identified_self(time);self.ledger.refresh_identity(entity);return entity
            if op==bytes([33,54]) and len(body)>=8:
                map_id=int.from_bytes(body[4:8],'little')
                token=(int.from_bytes(body[:4],'little'),map_id)
                if map_id!=self.map_id:
                    self.ledger.finish('zone_change');world.zone_reset();self.map_id=map_id
                    self.zone_sequence+=1;self.ledger.set_location(map_id,self.zone_sequence,token[0])
                elif token!=self.map_token:
                    # A same-map reload/teleport does not prove a new instance.
                    # Keep confirmed entities and the run; record the load token only.
                    self.ledger.set_location(map_id,self.zone_sequence,token[0])
                    self.decisions['zone:same_map_reload']+=1
                self.map_token=token
                return
            if op==bytes([5,56]):
                decision=periodic_message(body,self.skill_policy)
                self.decisions['periodic:'+decision.status+':'+decision.reason]+=1
                if decision.status in ('unclassified','rejected'):
                    try:
                        from .damage import checked_entity
                        probe=Cursor(body);target=checked_entity(probe);effect=probe.uint(1);source=checked_entity(probe)
                        # Healing, buffs on self, and player-target effects do not
                        # make damage coverage incomplete.
                        if effect not in (1,9,11) and target!=source and (target not in world.people or (self.ledger.track_pvp and not world.authorized(target))):
                            self.ledger.issue('periodic:'+decision.reason,source,time)
                    except InvalidData:pass
                if time is not None:
                    for hit in decision.hits:self.ledger.accept(time,hit)
                return decision
            elif op==bytes([65,54]):
                from .summons import spawn_role
                from .damage import checked_entity
                cursor=Cursor(body);entity=checked_entity(cursor);kind=cursor.uint(1)
                world.respawn(entity)
                summon=spawn_role(body)
                if summon is not None:
                    bound=world.summon(summon)
                    if world.self_entity is not None:self.ledger.refresh_identity(world.self_entity)
                    self.decisions['summon:bound' if bound else 'summon:pending']+=1
                elif kind in (0x04,0x0c,0x0d,0x1c):
                    from .entities import npc_spawn
                    metadata=npc_spawn(body)
                    if kind==0x04 and (metadata is None or metadata.template not in self.npc_policy.facts):
                        self.decisions['spawn:unclassified']+=1;return None
                    npc=world.npc(entity)
                    if npc:npc.origin='spawn'
                    if npc and metadata:
                        npc.template=metadata.template;npc.position=metadata.position;npc.spawn_hp_candidate=metadata.hp_candidate
                        fact=self.npc_policy.facts.get(npc.template)
                        if fact:npc.name=fact.name;npc.is_boss=fact.is_boss;npc.name_source=fact.provenance
                    self.decisions['spawn:npc']+=1
                else:self.decisions['spawn:unclassified']+=1
                return summon
            elif op==bytes([0,141]):
                from .entities import remain_health
                record=remain_health(body)
                if time is not None:self.ledger.health(record,time)
                return record
            elif op==bytes([27,146]):
                from .entities import health_pair
                record=health_pair(body)
                if time is not None:self.ledger.health(record,time)
                return record
            elif op==bytes([66,54]):
                from .entities import death
                entity,reason=death(body)
                if time is not None:self.ledger.entity_end(entity,reason,time)
                return entity,reason
            elif op==bytes([4,141]):
                from .entities import kill_credit
                entity,reason,killer=kill_credit(body)
                if killer:
                    world.identity(killer[0],killer[1],killer[2]);self.ledger.refresh_identity(killer[0])
                if time is not None:self.ledger.entity_end(entity,reason,time)
                return entity,reason
            elif op==bytes([33,141]):
                from .entities import battle
                entity,active,deadline=battle(body,time)
                if time is not None:self.ledger.battle(entity,active,time)
                return entity,active,deadline
            else:self.decisions['unsupported:'+op.hex(' ')]+=1
        except InvalidData as error:
            self.errors[op.hex(' ')+':'+str(error)]+=1
            if op==bytes([2,151]):
                if world.members:self.ledger.issue('group_metadata',time=time)
                world.party_trusted=False
                if self.ledger.active:self.ledger.fight_group_state='invalid'
            elif op in (bytes.fromhex('0092'),bytes.fromhex('0296'),bytes.fromhex('0d92'),bytes.fromhex('0a96')):
                if str(error)!='login roster missing local proof':self.deferred_login=None
                self.login_membership=None;world.party_trusted=False
                if self.ledger.active:self.ledger.fight_group_state='invalid'
            elif op==bytes([51,54]):
                self.ledger.issue('self_metadata',time=time)
                self.ledger.finish('identity_lost');world.reset()
