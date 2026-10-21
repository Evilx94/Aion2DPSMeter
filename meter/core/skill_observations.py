"""Observed skill catalog, separate from player authorization and combat totals."""
from collections import Counter
from .binary import Cursor,InvalidData
from .damage import damage_message,periodic_message,periodic_fields,checked_entity
from .skill_policy import SkillPolicy

class SkillObservations:
    def __init__(self,policy=None):
        self.policy=policy or SkillPolicy.builtin();self.records={};self.decisions=Counter();self.messages=0
    def record(self,skill,time):
        return self.records.setdefault(skill,{'skill':skill,'first_ms':time,'last_ms':time,'events':Counter(),'amounts':Counter(),'unclassified_reasons':Counter()})
    def accept(self,message,time):
        self.messages+=1;op=message.opcode;body=message.body
        if op==bytes.fromhex('0238'):
            try:
                c=Cursor(body);checked_entity(c)
                if c.uint(1)!=0:raise InvalidData('unconfirmed cast header')
                skill=c.uint(4)
                if not 1<=skill<=299999999:raise InvalidData('cast skill range')
                r=self.record(skill,time);r['events']['cast']+=1;r['last_ms']=time
            except InvalidData as e:self.decisions['cast_rejected:'+str(e)]+=1
            return
        if op not in (bytes.fromhex('0438'),bytes.fromhex('0538')):return
        result=damage_message(body) if op==bytes.fromhex('0438') else periodic_message(body,self.policy)
        self.decisions[op.hex(' ')+':'+result.status+':'+result.reason]+=1
        for hit in result.hits:
            r=self.record(hit.skill,time);r['last_ms']=time
            event='healing' if hit.kind=='heal' else ('dot_tick' if hit.periodic else 'direct_damage')
            r['events'][event]+=1;r['amounts']['healing' if hit.kind=='heal' else 'damage']+=hit.amount
            if hit.periodic and hit.kind=='damage':r['amounts']['dot_damage']+=hit.amount
        if op==bytes.fromhex('0538') and result.status!='accepted':
            try:
                fields=periodic_fields(body);r=self.record(fields.skill,time);r['last_ms']=time
                if result.status=='ignored':r['events']['non_damage_periodic']+=1
                else:r['events']['unclassified_periodic']+=1;r['unclassified_reasons'][result.reason]+=1
            except InvalidData:pass
    def snapshot(self):
        return {'messages':self.messages,'decisions':dict(self.decisions),'skills':[{**r,'events':dict(r['events']),'amounts':dict(r['amounts']),'unclassified_reasons':dict(r['unclassified_reasons'])} for _,r in sorted(self.records.items())]}
