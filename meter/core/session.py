"""Capture integration candidate, isolated from historical parser modules."""
from collections import Counter
from .binary import Cursor,InvalidData
from .framing import messages
from .combat import Ledger
from .parser import Parser
from .transport import Stream
from .skill_labels import SkillLabels,label_row
class Decoder:
    def __init__(self,emit,loss,aligned=False):
        self.emit=emit;self.loss=loss;self.buffer=bytearray();self.hunting=not aligned;self.stats=Counter();self.offset=0;self.frame_span=(0,0);self.frame_header_end=0
    def consume(self,count):
        del self.buffer[:count];self.offset+=count
    def reset(self):
        self.stats['dropped_bytes']+=len(self.buffer);self.offset+=len(self.buffer);self.buffer.clear();self.hunting=True
    def feed(self,data,time,start=None):
        if start is not None and not self.buffer:self.offset=start
        self.buffer.extend(data)
        if len(self.buffer)>8*1024*1024:self.reset();self.loss();raise ValueError('frame buffer limit')
        while self.buffer:
            if self.hunting:
                choices=[self.buffer.find(signature) for signature in (bytes([14,0,54]),bytes([6,0,54]))]
                choices=[at for at in choices if at>=0]
                if not choices:
                    cut=max(0,len(self.buffer)-2);self.stats['dropped_bytes']+=cut;self.consume(cut);return
                cut=min(choices);self.stats['dropped_bytes']+=cut;self.consume(cut);self.hunting=False
            if self.buffer[0]==0:self.consume(1);continue
            try:
                probe=Cursor(bytes(self.buffer));value=probe.variable();size=value+probe.position-4
            except InvalidData:
                if len(self.buffer)<5:return
                self.discard();continue
            if not probe.position+2<=size<=65535:self.discard();continue
            if len(self.buffer)<size:return
            self.frame_span=(self.offset,self.offset+size);self.frame_header_end=self.offset+probe.position+2+(1 if 240<=self.buffer[probe.position]<=254 else 0);raw=bytes(self.buffer[:size]);self.consume(size)
            try:decoded=list(messages(raw))
            except InvalidData:self.stats['invalid_frames']+=1;self.loss();self.hunting=True;continue
            for message in decoded:self.stats['messages']+=1;self.emit(message,time)
    def discard(self):
        self.consume(1);self.stats['dropped_bytes']+=1;self.stats['invalid_frames']+=1;self.hunting=True;self.loss()
class Session:
    def __init__(self,party_only=True,preferred_identity=None,track_pvp=False,skill_labels=None,npc_policy=None,encounters=None):
        from collections import deque
        self.skill_labels=skill_labels if skill_labels is not None else SkillLabels.builtin()
        self.ledger=Ledger(party_only=party_only,track_pvp=track_pvp,encounters=encounters);self.ledger.world.set_preferred_identity(preferred_identity);self.parser=Parser(self.ledger,npc_policy=npc_policy)
        self.stream=None;self.key=None;self.decoder=None;self.partial=False
        self.stats=Counter();self.syn_sequence=None;self.retired_flows=deque(maxlen=32)
        self.frame_consumers=deque();self.dependencies={};self.activity_dependencies={};self.local_proofs={};self.transport_totals=Counter();self.framing_totals=Counter()
        from .network import TcpTelemetry
        self.network=TcpTelemetry()
    def reset_world(self):
        self.ledger.world.reset();self.parser.reset_location();self.local_proofs.clear()
    def loss(self):
        self.network.invalidate()
        self.partial=True;self.ledger.issue('capture_loss');self.ledger.capture_partial=True
        # Freeze target/self metadata before invalidating any cache.
        self.ledger.finish('capture_loss');self.ledger.capture_partial=True;self.reset_world();self.dependencies.clear();self.activity_dependencies.clear()
        if self.decoder:self.decoder.reset()
    def conflict(self):
        offsets=self.stream.conflict_offsets if self.stream else set()
        self.ledger.unassigned.conflict(offsets)
        affected=set();mapped=False;header_conflict=False
        for start,end,header_end,identifiers in self.frame_consumers:
            matching=[at for at in offsets if start<=at<end]
            if matching:
                mapped=True;affected.update(identifiers)
                if any(at<header_end for at in matching):header_conflict=True
        if header_conflict:
            # A changed length/opcode invalidates alignment and all downstream
            # consumers of this connection, not fights preceding the frame.
            first=min(offsets)
            for start,end,header_end,identifiers in self.frame_consumers:
                if end>first:affected.update(identifiers)
            if self.ledger.active:affected.add(self.ledger.sequence+1)
        for start,end,consumers in self.dependencies.values():
            if any(start<=at<end for at in offsets):
                affected.update(consumers)
                if self.ledger.active:affected.add(self.ledger.sequence+1)
        # Unmapped bytes can affect the in-progress frame, not completed history.
        if not affected and mapped and not header_conflict:return
        if not affected and self.ledger.active:affected.add(self.ledger.sequence+1)
        active_affected=bool(self.ledger.active and self.ledger.sequence+1 in affected)
        self.ledger.invalidate(affected)
        if not active_affected and affected and all(identifier<=self.ledger.sequence for identifier in affected) and not (self.stream and any(at>=self.stream.next for at in offsets)):
            return
        self.loss()
    def emit(self,message,time):
        before=self.ledger.sequence+1 if self.ledger.active else None
        previous_own=self.ledger.world.people.get(self.ledger.world.self_entity)
        previous_roster_dependency=self.dependencies.get(bytes([2,151]))
        generation=self.ledger.world.generation
        count=len(self.ledger.active);closed_count=self.ledger.sequence;issues=dict(self.ledger.issues)
        activity_revision=self.ledger.activity_revision
        deferred_revision=self.ledger.deferred_damage.revision
        unassigned_serial=self.ledger.unassigned.serial
        result=self.parser.accept(message,time)
        if generation!=self.ledger.world.generation:
            self.dependencies.clear();self.activity_dependencies.clear();self.local_proofs.clear()
            if message.opcode==bytes([33,54]) and previous_roster_dependency:self.dependencies[bytes([2,151])]=previous_roster_dependency
        # A complete heartbeat/framed record establishes byte alignment only;
        # self/group authorization still requires fresh metadata after a gap.
        self.partial=False
        after=self.ledger.sequence+1 if self.ledger.active else None
        changed=(len(self.ledger.active)!=count or self.ledger.sequence!=closed_count or dict(self.ledger.issues)!=issues or self.ledger.activity_revision!=activity_revision)
        identifiers={x for x in (before,after) if x is not None} if changed else set()
        if self.ledger.deferred_damage.revision!=deferred_revision:
            identifiers.update(self.ledger.deferred_damage.recovered)
            self.ledger.deferred_damage.recovered.clear()
            if self.ledger.active:identifiers.add(self.ledger.sequence+1)
        start,end=self.decoder.frame_span
        self.ledger.unassigned.bind_frames(unassigned_serial,start,end)
        if self.frame_consumers and self.frame_consumers[-1][0:2]==(start,end):
            self.frame_consumers[-1][3].update(identifiers)
        else:self.frame_consumers.append((start,end,self.decoder.frame_header_end,identifiers))
        if message.opcode==bytes([74,54]) and result is not None:
            proof=self.local_proofs.setdefault(result.entity,[])
            if len(proof)<2 and (not proof or proof[-1][0]!=time):proof.append((time,self.frame_consumers[-1][3]))
            if len(self.local_proofs)>8:self.local_proofs.pop(next(iter(self.local_proofs)))
        # These frames can determine the interpretation of later combat events.
        current_own=self.ledger.world.people.get(self.ledger.world.self_entity)
        if message.opcode in (bytes([69,54]),bytes([68,54]),bytes([4,141]),bytes([74,54]),bytes([65,54])) and current_own and current_own!=previous_own:
            self.dependencies[bytes([51,54])]=(start,end,self.frame_consumers[-1][3])
        if message.opcode in (bytes([51,54]),bytes([2,151])):
            self.dependencies[message.opcode]=(start,end,self.frame_consumers[-1][3])
        if message.opcode in (bytes.fromhex('0092'),bytes.fromhex('0296'),bytes.fromhex('0d92'),bytes.fromhex('0a96')) and result is not None:
            member_id=result.get('id') if isinstance(result,dict) else 'snapshot'
            self.dependencies[('login_group',message.opcode,member_id)]=(start,end,self.frame_consumers[-1][3])
        if message.opcode==bytes.fromhex('1c92') and result is not None:
            self.dependencies[('login_group',message.opcode,result.character_id)]=(start,end,self.frame_consumers[-1][3])
        if message.opcode in (bytes([69,54]),bytes([68,54])) and type(result) is int:
            self.dependencies[('player',result)]=(start,end,self.frame_consumers[-1][3])
        if message.opcode==bytes([65,54]) and result is not None and hasattr(result,'entity'):
            self.dependencies[('summon',result.entity)]=(start,end,self.frame_consumers[-1][3])
            if len(self.dependencies)>2050:
                oldest=next(k for k in self.dependencies if isinstance(k,tuple));self.dependencies.pop(oldest)
        if self.parser.listed_activity:
            entity=self.parser.listed_activity[0].entity;key=('buff_list',entity)
            self.dependencies[key]=(start,end,self.frame_consumers[-1][3])
            self.activity_dependencies.setdefault(entity,set()).add(key)
        if message.opcode in (bytes.fromhex('0238'),bytes.fromhex('0338')) and result is not None and hasattr(result,'actor') and self.ledger.world.authorized(result.actor) and self.ledger.world.resolve(result.actor)==result.actor:
            key=('cast' if message.opcode==bytes.fromhex('0238') else 'hit_notice',result.actor);self.dependencies[key]=(start,end,self.frame_consumers[-1][3])
            actor=self.ledger.world.resolve(result.actor);self.activity_dependencies.setdefault(actor,set()).add(key)
        if message.opcode in (bytes.fromhex('2a38'),bytes.fromhex('2b38'),bytes.fromhex('2c38')) and result is not None and self.ledger.world.authorized(result.entity):
            key=('buff',result.entity,result.instance);self.dependencies[key]=(start,end,self.frame_consumers[-1][3])
            self.activity_dependencies.setdefault(result.entity,set()).add(key)
        while len(self.dependencies)>4098:
            oldest=next(key for key in self.dependencies if isinstance(key,tuple));self.dependencies.pop(oldest)
        if identifiers:
            for key,dependency in self.dependencies.items():
                if isinstance(key,tuple) and key[0]=='login_group':
                    dependency[2].update(identifiers);dependency[2].intersection_update(range(max(1,self.ledger.sequence-29),self.ledger.sequence+2))
            if self.ledger.world.self_recognition=='local_updates':
                for stamp,consumers in self.local_proofs.get(self.ledger.world.self_entity,()):
                    consumers.update(identifiers);consumers.intersection_update(range(max(1,self.ledger.sequence-29),self.ledger.sequence+2))
            for key in (bytes([51,54]),bytes([2,151])):
                dependency=self.dependencies.get(key)
                if dependency:
                    dependency[2].update(identifiers);dependency[2].intersection_update(range(max(1,self.ledger.sequence-29),self.ledger.sequence+2))
            for hit in getattr(result,'hits',()):
                source=hit.source;visited=set()
                while source not in visited:
                    visited.add(source);player_dependency=self.dependencies.get(('player',source))
                    if player_dependency:
                        player_dependency[2].update(identifiers);player_dependency[2].intersection_update(range(max(1,self.ledger.sequence-29),self.ledger.sequence+2))
                    dependency=self.dependencies.get(('summon',source))
                    if dependency:
                        dependency[2].update(identifiers);dependency[2].intersection_update(range(max(1,self.ledger.sequence-29),self.ledger.sequence+2))
                    if source not in self.ledger.world.owners:break
                    source=self.ledger.world.owners[source]
        if identifiers:
            actors=set(self.ledger.active_actors)
            if self.ledger.world.self_entity is not None:actors.add(self.ledger.world.self_entity)
            for actor in actors:
                keys=self.activity_dependencies.get(actor,set())
                for key in tuple(keys):
                    dependency=self.dependencies.get(key)
                    if dependency is None:keys.discard(key);continue
                    dependency[2].update(identifiers);dependency[2].intersection_update(range(max(1,self.ledger.sequence-29),self.ledger.sequence+2))
        for fight in self.ledger.closed:
            fight.setdefault('connection_epoch',self.stats['connections'])
        if self.stream:
            lower=self.stream.next-self.stream.history_limit
            while self.frame_consumers and self.frame_consumers[0][1]<lower:self.frame_consumers.popleft()
    def feed(self,data,time):
        self.decoder.feed(data,time,self.stream.delivery_start)
    def archive_transport(self):
        if self.stream:self.transport_totals.update(self.stream.stats)
        if self.decoder:self.framing_totals.update(self.decoder.stats)
    def packet(self,packet):
        self.stats['packets']+=1
        if packet is None or packet.source_port!=13328:return
        key=(packet.source,packet.source_port,packet.destination,packet.destination_port)
        syn=bool(packet.flags&2)
        if key in self.retired_flows and not syn:self.stats['retired_flow']+=1;return
        if self.key is not None and key!=self.key and not syn:self.stats['other_flow']+=1;return
        sequence=(packet.sequence+(1 if syn else 0))%2**32
        if self.stream is None or key!=self.key or (syn and self.syn_sequence!=packet.sequence):
            if self.stream:
                self.stream.flush_gap();self.ledger.finish('connection_change');self.archive_transport()
                if self.key!=key:self.retired_flows.append(self.key)
            self.reset_world();self.ledger.integrity='ok';self.dependencies.clear();self.activity_dependencies.clear();self.frame_consumers.clear()
            if key in self.retired_flows:self.retired_flows.remove(key)
            self.stats['connections']+=1;self.ledger.connection_epoch=self.stats['connections'];self.key=key;self.syn_sequence=packet.sequence if syn else None
            self.network.select(key)
            self.partial=not syn;self.ledger.capture_partial=not syn
            self.decoder=Decoder(self.emit,self.loss,aligned=syn)
            self.stream=Stream(self.feed,self.loss,self.conflict,sequence)
        time=max(packet.time_ms,self.ledger.time)
        self.stream.push(sequence,packet.payload,time)
        if packet.flags&5:
            self.stream.flush_gap();self.ledger.finish('connection_closed');self.archive_transport()
            self.retired_flows.append(key);self.stream=None;self.key=None;self.decoder=None
            self.network.select(None)
            self.reset_world();self.dependencies.clear();self.activity_dependencies.clear();self.frame_consumers.clear()
    def manual_self_name(self,actor,name):
        from .parser import text
        from ..language import tr
        encoded=name.encode('utf-8');text(Cursor(encoded),len(encoded))
        world=self.ledger.world;person=world.people.get(actor)
        if person is None:raise ValueError(tr('Entity wurde noch nicht als Spieler beobachtet.'))
        if person.confirmed and person.name.casefold()!=name.casefold():raise ValueError(tr('Entity hat einen anderen bestätigten Namen.'))
        matching=[(label,server) for label,server in world.members if label.casefold()==name.casefold()]
        label,server=matching[0] if len(matching)==1 else (name,person.server)
        if world.self_entity is not None and world.self_entity!=actor:self.ledger.finish('manual_character_change');world.reset()
        world.identity(actor,label,server,True,person.confirmed,person.class_name,person.name_source if person.confirmed else 'manual')
        world.self_recognition='manual';self.ledger.identified_self(self.ledger.time)
    def snapshot(self,now_ms=None):
        world=self.ledger.world;fights=self.ledger.snapshot();own=world.people.get(world.self_entity)
        for fight in fights:
            for row in fight.get('skills',[]):label_row(row,self.skill_labels)
            for row in fight.get('cast_usage',[]):label_row(row,self.skill_labels)
            from .skill_labels import label_buff_row
            for row in fight.get('buffs',[]):label_buff_row(row,self.skill_labels)
        latest=fights[-1] if fights else {}
        transport=self.transport_totals+(self.stream.stats if self.stream else Counter())
        network=self.network.snapshot(now_ms)
        network.update(capture_gap_bytes=transport['gap_bytes'],capture_gaps=transport['gap_events'])
        from ..group_identity import identity_status
        return {'fights':fights,'scope':'self_and_party' if self.ledger.party_only else 'all','network':network,
                'partial':self.partial,'messages':sum(self.parser.counts.values()),'decisions':dict(self.parser.decisions),
                'parser_errors':dict(self.parser.errors),'packets':self.stats['packets'],
                'self_id':world.self_entity,'map_id':self.parser.map_id,'party_trusted':world.party_trusted,
                'group_state':('invalid' if not world.party_trusted else ('missing' if not world.party_known else ('partial' if not world.party_complete else ('members' if world.party_records else 'solo')))),
                'roster':[dict(m) for m in world.party_records],
                'group_identity':identity_status(world),
                'group_membership_source':world.party_source,
                'party_entities':[{'id':actor,'name':link[0],'server':link[1]} for actor,link in world.party_links.items()],
                'identity_candidates':[{'id':p.entity,'name':p.name,'class':p.class_name} for p in world.people.values()],
                'self_identity':{'id':world.self_entity,'name':own.name if own else '', 'server':own.server if own else 0,
                                 'source':own.name_source if own else '', 'confirmed':bool(own and own.confirmed), 'recognition':world.self_recognition, 'token':world.identity_token(world.self_entity)},
                'unresolved_owner_events':self.ledger.unresolved_owner_events,
                'coverage_incomplete':latest.get('coverage_incomplete',False),
                'framing':dict(self.framing_totals+(self.decoder.stats if self.decoder else Counter())),
                'transport':dict(self.transport_totals+(self.stream.stats if self.stream else Counter()))}
