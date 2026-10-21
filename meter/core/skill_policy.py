"""Exact periodic classifications with separate own and reference provenance."""
from dataclasses import dataclass
from types import MappingProxyType
@dataclass(frozen=True)
class Fact:
    skill:int
    classification:str
    provenance:str
    name:str=''
class SkillPolicy:
    def __init__(self,facts=()):
        records={}
        for fact in facts:
            if not 1<=fact.skill<=299999999:raise ValueError('skill range')
            if fact.classification not in ('damage_dot','healing'):raise ValueError('classification')
            if not fact.provenance.strip():raise ValueError('provenance required')
            if fact.skill in records:raise ValueError('duplicate skill classification')
            records[fact.skill]=fact
        self.facts=MappingProxyType(records)
    @classmethod
    def builtin(cls):
        from ..catalog_store import records
        return cls(Fact(item['skill'],item['classification'],item['provenance']) for item in records('periodic_skills.json','facts'))
    def damage_dot(self,skill):
        fact=self.facts.get(skill)
        return bool(fact and fact.classification=='damage_dot')
