"""NPC labels with provenance and optional runtime catalogs."""
from dataclasses import dataclass
from types import MappingProxyType
@dataclass(frozen=True)
class NpcFact:
    template:int
    name:str
    is_boss:bool
    provenance:str
class NpcPolicy:
    def __init__(self,facts=()):
        records={}
        for fact in facts:
            if type(fact.template) is not int or not 1<=fact.template<=16777215 or not isinstance(fact.name,str) or not fact.name.strip() or len(fact.name)>80 or type(fact.is_boss) is not bool or not isinstance(fact.provenance,str) or not fact.provenance.strip():raise ValueError('NPC fact requires ID, label and provenance')
            if fact.template in records:raise ValueError('duplicate NPC label')
            records[fact.template]=fact
        self.facts=MappingProxyType(records)
    @classmethod
    def builtin(cls):
        from ..catalog_store import records
        return cls(NpcFact(f['template'],f['name'],f['is_boss'],f['provenance']) for f in records('npc_labels.json','facts',own_only=True))

    @classmethod
    def configured(cls,path):
        import json
        from pathlib import Path
        base=cls.builtin()
        try:
            document=json.loads(Path(path).read_text(encoding='utf-8'))
            if document.get('schema')!=1:return base
            extra=cls(NpcFact(r['template'],r['name'],r['is_boss'],r['provenance']) for r in document['facts'])
        except (OSError,ValueError,TypeError,KeyError):return base
        return cls({**extra.facts,**base.facts}.values())
    @classmethod
    def for_runtime(cls,directory):
        from ..catalog_store import records
        return cls(NpcFact(f['template'],f['name'],f['is_boss'],f['provenance']) for f in records('npc_labels.json','facts'))
