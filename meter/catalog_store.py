"""Minimal runtime catalogs. Development evidence is never needed by the live meter."""
from functools import lru_cache
from pathlib import Path
import json

DATA = Path(__file__).parent / 'data'
LOCAL_LABEL='Local catalog'


@lru_cache(maxsize=8)
def document(filename):
    if filename not in {'skill_labels.json','npc_labels.json','dungeon_labels.json',
                        'buff_labels.json','periodic_skills.json'}:
        raise ValueError('unknown catalog')
    result=json.loads((DATA/filename).read_text(encoding='utf-8'))
    if result.get('schema')!=1 or result.get('catalog_role')!='runtime_local':
        raise ValueError('runtime catalog schema')
    return result


def records(filename, section, own_only=False):
    """Keep the legacy built-in subset setting without loading source history."""
    for item in document(filename).get(section,[]):
        if own_only and not item.get('builtin',False):continue
        field='provenance' if filename in ('npc_labels.json','periodic_skills.json') else 'source'
        yield {**item,field:LOCAL_LABEL}
