"""Exact catalog names and documented Theostone ID normalization only."""
from dataclasses import dataclass
from pathlib import Path
from functools import lru_cache
import json

@dataclass(frozen=True)
class SkillLabel:
    skill:int
    name:str
    source:str
    icon_skill:int
    match:str="exact"

def specialization_key(identifier):
    """Numerical pattern only; suffix semantics are not inferred."""
    tail=identifier%10000
    prefix=tail//10
    digits=str(prefix) if prefix else ''
    if any(d not in '12345' for d in digits) or ''.join(sorted(set(digits)))!=digits:return None
    return identifier-tail,tail%10

@lru_cache(maxsize=1)
def _bolt_rune_selections():
    from ..catalog_store import records
    return {row['skill']:tuple(row['rune_selection']['slots']) for row in records('skill_labels.json','records')
            if 17060000<=row['skill']<17070000 and row.get('rune_selection',{}).get('status')=='confirmed_exact'}


def bolt_rune_selection(identifier):
    """Exact tested setups, or a marked Bolt-only charge-prefix derivation."""
    if type(identifier) is not int or not 17060000<=identifier<17070000:return None
    tested=_bolt_rune_selections()
    if identifier in tested:return {'slots':list(tested[identifier]),'status':'confirmed_exact'}
    prefix=(identifier%10000)//10
    matches={slots for key,slots in tested.items() if (key%10000)//10==prefix}
    if identifier%10 in (0,1,2,3) and len(matches)==1:
        return {'slots':list(next(iter(matches))),'status':'derived_charge_variant'}
    return None

def rune_selection(identifier,labels):
    """Tested Bolt mappings, otherwise an explicitly unverified player-skill pattern."""
    bolt=bolt_rune_selection(identifier)
    if bolt is not None:return bolt
    if type(identifier) is not int or not 11_000_000<=identifier<20_000_000:return None
    family=identifier-identifier%10000
    if family==17060000 or family%1_000_000==0:return None
    if (family,identifier%10) in PATTERN_EXCLUSIONS:return None
    parent=labels.lookup(family)
    if parent is None:return None
    # Internal spirit selectors and summon/return commands do not use the
    # ordinary three-slot interpretation even when their digits look similar.
    if parent.name.startswith(('Summon:', 'Dismiss:', 'Return:', 'Fire Spirit:', 'Water Spirit:', 'Wind Spirit:', 'Earth Spirit:', 'Ancient Spirit:')):return None
    digits=f'{(identifier%10000)//10:03}'.lstrip('0')
    if any(d not in '12345' for d in digits) or len(set(digits))!=len(digits):return None
    return {'slots':[int(d) for d in digits],'status':'pattern_candidate'}

# A leave-one-out audit found counterexamples for these numeric templates.
# Exclude them from variant-name inference; exact names still take priority.
PATTERN_EXCLUSIONS={(15410000,1),(19060000,0),(19380000,0)}
DISPLAY_CANDIDATE_MATCHES={'family','family_parent','variant_pattern','user_candidate','effect_family'}

class SkillLabels:
    def __init__(self,records):
        self.labels={}
        for row in records:
            skill=row['skill'];name=row['name'];source=row['source']
            if type(skill) is not int or not 1<=skill<=299999999 or not isinstance(name,str) or not name.strip() or not isinstance(source,str) or not source.strip():raise ValueError('invalid skill label')
            ids=[skill]+row.get('aliases',[])
            for identifier in ids:
                if type(identifier) is not int or not 1<=identifier<=299999999 or identifier in self.labels:raise ValueError('duplicate/invalid exact alias')
                self.labels[identifier]=SkillLabel(identifier,name,source,row.get('icon_skill',skill))
        self.rebuild_families()
    def rebuild_families(self):
        groups={}
        for identifier,label in self.labels.items():
            if 11_000_000<=identifier<20_000_000:
                groups.setdefault(identifier-identifier%10000,[]).append(label)
        effect_groups={}
        for identifier,label in self.labels.items():
            if 30_000_000<=identifier<31_000_000 and identifier%10==1 and label.name.startswith('Theostone:'):
                effect_groups.setdefault(identifier//10,[]).append(label)
        self.reduced_effects={key:items[0] for key,items in effect_groups.items()
                              if len({' '.join(item.name.casefold().split()) for item in items})==1}
        self.families={}
        self.parents={family:self.labels[family] for family in groups if family in self.labels}
        pattern_groups={}
        for identifier,label in self.labels.items():
            if not 11_000_000<=identifier<20_000_000:continue
            key=specialization_key(identifier)
            if key is not None:pattern_groups.setdefault(key,[]).append(label)
        self.patterns={}
        for key,items in pattern_groups.items():
            if key in PATTERN_EXCLUSIONS or len(items)<2:continue
            if len({' '.join(item.name.casefold().split()) for item in items})==1:
                self.patterns[key]=items[0]
        for family,labels in groups.items():
            base=self.labels.get(family)
            if base and len({' '.join(label.name.casefold().split()) for label in labels})==1:
                self.families[family]=base
    @classmethod
    def builtin(cls):
        from ..catalog_store import records
        labels=cls(records('skill_labels.json','records',own_only=True))
        return labels
    @classmethod
    def configured(cls,path):
        base=cls.builtin()
        if not path:return base
        try:
            document=json.loads(Path(path).read_text(encoding='utf-8'))
            if document.get('schema')!=1:return base
            extra=cls(document['records'])
        except (OSError,ValueError,KeyError,TypeError):return base
        # Built-in exact labels take precedence; no aliases are inferred here.
        base.labels={**extra.labels,**base.labels};base.rebuild_families();return base
    @classmethod
    def for_runtime(cls,directory,settings):
        if not settings.get('skill_names_enabled',True):return cls.builtin()
        from ..catalog_store import records
        bundled=cls(records('skill_labels.json','records'))
        path=settings.get('skill_names_file')
        if not path or not Path(path).is_file():return bundled
        # Explicit user additions remain optional; no private reference auto-discovery.
        custom=cls.configured(path)
        custom.labels={**bundled.labels,**custom.labels};custom.rebuild_families()
        return custom
    def lookup(self,skill):return self.labels.get(skill)
    def display_lookup(self,skill):
        exact=self.lookup(skill)
        if exact:return exact
        if type(skill) is not int:return None
        effect=self.reduced_effects.get(skill)
        if effect:return SkillLabel(skill,effect.name,f'Documented reduced Theostone ID: {skill} -> {effect.skill} (ID * 10 + 1). Naming only; damage and DoT policy unchanged. '+effect.source,effect.icon_skill,'effect_family')
        key=specialization_key(skill)
        if key and key[0]==17060000 and key[1] in (1,2,3):
            canonical=self.lookup(skill-key[1])
            if canonical and canonical.name=='Bolt':
                return SkillLabel(skill,'Bolt','Bolt charge stages 1/2/MAX: exact canonical catalog and own Cleric charge-1/2/MAX capture 2026-10-13; specialization slots remain separate.',canonical.icon_skill,'charge_variant')
        # Class utility actions use canonical ...000100 Dodge; they have no
        # canonical ...000000 skill parent. Naming remains a marked parent,
        # never an invented exact interpretation of suffix 01.
        if 11_000_000<=skill<20_000_000 and skill%1_000_000==101:
            parent=self.lookup(skill-1)
            if parent and parent.name=='Dodge':
                from ..language import tr
                return SkillLabel(skill,parent.name,tr('Basis-ID {0}; genauer Untereffekt der ID {1} unbekannt. Utility subfamily, no damage/effect inference. ',parent.skill,skill)+parent.source,parent.icon_skill,'family_parent')
        if 11_000_000<=skill<20_000_000:
            family=skill-skill%10000
            parent=self.lookup(family)
            if parent:
                from ..language import tr
                return SkillLabel(skill,parent.name,tr('Basis-ID {0}; genauer Untereffekt der ID {1} unbekannt. Nur Familienanzeige, keine Aussage über Schaden, Heilung, DoT oder Auslöser. ',family,skill)+parent.source,parent.icon_skill,'family_parent')
        # Without an exact entry or known canonical parent, keep the name open.
        return None

def label_row(row,labels):
    for field in ('charge_level','specialization_slots','specialization_status'):row.pop(field,None)
    fact=labels.display_lookup(row['skill'])
    if fact:
        row.update(name=fact.name,name_source=fact.source,icon_skill=fact.icon_skill,name_match=fact.match)
    else:
        # Re-evaluate historical labels too; speculative saved names must not survive.
        row.update(name='?',name_source='Nicht zugeordnet',name_match='unknown')
        row.pop('icon_skill',None)
    key=specialization_key(row['skill'])
    if key and key[0]==17060000 and key[1] in (1,2,3) and fact:
        canonical=labels.lookup(row['skill']-key[1])
        if canonical and canonical.name=='Bolt':
            row['charge_level']=key[1]
    runes=rune_selection(row['skill'],labels)
    if runes:
        row['specialization_slots']=runes['slots'];row['specialization_status']=runes['status']
    return row


def label_buff_row(row,labels):
    """Use an explicit wire skill link as a display hint, never an effect fact."""
    from ..language import tr
    if row.get('name') not in (None,'','?') and row.get('name_match') not in ('associated_skill','unknown'):
        return row
    skill=row.get('skill',0);fact=labels.display_lookup(skill) if skill else None
    row['effect_name_confirmed']=False
    if fact:
        row.update(name=tr('{0} · Effekt {1}',fact.name,row['abnormal']),skill_name=fact.name,
                   name_source=tr('Skill-ID aus der Buffmeldung: {0}; genauer Effektname unbestätigt.',skill),
                   name_match='associated_skill')
    else:
        row.update(name=tr('Unbekannter Effekt {0}',row['abnormal']),name_match='unknown')
    return row
