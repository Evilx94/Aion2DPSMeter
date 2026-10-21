"""Map labels and boss-to-dungeon facts, independent of damage parsing."""
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
import json

@dataclass(frozen=True)
class MapFact:
    map_id:int
    name:str
    source:str
    kind:str='dungeon'

@dataclass(frozen=True)
class BossOrder:
    map_id:int
    template:int
    index:int
    source:str

@dataclass(frozen=True)
class BossLocation:
    template:int
    area_name:str
    source:str
    map_ids:tuple=()
    kind:str='dungeon'
    @property
    def dungeon_name(self):return self.area_name if self.kind=='dungeon' else ''


class EncounterCatalog:
    def __init__(self,maps=(),orders=(),boss_locations=()):
        locations={};sequence={}
        for item in maps:
            if type(item.map_id) is not int or not 1<=item.map_id<=0xffffffff or not isinstance(item.name,str) or not item.name.strip() or len(item.name)>120 or not isinstance(item.source,str) or not item.source.strip():raise ValueError('map fact')
            if item.kind not in ('dungeon','field'):raise ValueError('map kind')
            if item.map_id in locations:raise ValueError('duplicate map')
            locations[item.map_id]=item
        for item in orders:
            if type(item.map_id) is not int or item.map_id not in locations or type(item.template) is not int or not 1<=item.template<=0xffffff or type(item.index) is not int or not 1<=item.index<=100 or not isinstance(item.source,str) or not item.source.strip():raise ValueError('boss order fact')
            key=(item.map_id,item.template)
            if key in sequence:raise ValueError('duplicate boss order')
            sequence[key]=item
        associations={};seen=set()
        for item in boss_locations:
            if type(item.template) is not int or not 1<=item.template<=0xffffff or not isinstance(item.area_name,str) or not item.area_name.strip() or len(item.area_name)>120 or not isinstance(item.source,str) or not item.source.strip():raise ValueError('boss location fact')
            if not isinstance(item.map_ids,tuple) or any(type(m) is not int or not 1<=m<=0xffffffff for m in item.map_ids):raise ValueError('boss location map ids')
            if item.kind not in ('dungeon','field'):raise ValueError('boss location kind')
            key=(item.template,item.kind,item.area_name,item.map_ids)
            if key in seen:raise ValueError('duplicate boss location')
            seen.add(key);associations.setdefault(item.template,[]).append(item)
        self.boss_locations=MappingProxyType({k:tuple(v) for k,v in associations.items()})
        self.maps=MappingProxyType(locations);self.orders=MappingProxyType(sequence)
    @classmethod
    def from_document(cls,document):
        if document.get('schema')!=1:raise ValueError('encounter schema')
        return cls((MapFact(r['map_id'],r['name'],r['source'],r.get('kind','dungeon')) for r in document.get('maps',[])),
                   (BossOrder(r['map_id'],r['template'],r['index'],r['source']) for r in document.get('orders',[])),
                   (BossLocation(r['template'],r.get('area_name',r.get('dungeon_name')),r['source'],tuple(r.get('map_ids',[])),r.get('kind','dungeon')) for r in document.get('boss_locations',[])))
    @classmethod
    def builtin(cls):
        from ..catalog_store import records
        return cls.from_document({'schema':1,**{section:list(records('dungeon_labels.json',section,own_only=True)) for section in ('maps','orders','boss_locations')}})
    @classmethod
    def configured(cls,path):
        base=cls.builtin()
        try:extra=cls.from_document(json.loads(Path(path).read_text(encoding='utf-8')))
        except (OSError,ValueError,TypeError,KeyError):return base
        return cls({**extra.maps,**base.maps}.values(),{**extra.orders,**base.orders}.values(),
                   (item for group in {**extra.boss_locations,**base.boss_locations}.values() for item in group))
    @classmethod
    def for_runtime(cls,directory):
        from ..catalog_store import records
        return cls.from_document({'schema':1,**{section:list(records('dungeon_labels.json',section)) for section in ('maps','orders','boss_locations')}})
    def order(self,map_id,template):return self.orders.get((map_id,template))

    def locations_for(self,template):return self.boss_locations.get(template,())
    def location_for_boss(self,template,map_id=None):
        candidates=self.locations_for(template)
        if map_id is None:
            return candidates[0] if len({(item.kind,item.area_name) for item in candidates})==1 else None
        fact=self.maps.get(map_id)
        matching=[item for item in candidates if map_id in item.map_ids or (fact and fact.kind==item.kind and fact.name.casefold()==item.area_name.casefold())]
        return matching[0] if len({(item.kind,item.area_name) for item in matching})==1 else None
    def dungeon_for_boss(self,template,map_id=None):
        item=self.location_for_boss(template,map_id)
        return item if item and item.kind=='dungeon' else None
