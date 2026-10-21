"""Complete recorded dungeon JSON export, without inferring missing fights."""
from .language import tr as _tr
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
import json
from .chat_export import run_identity

def dungeon_log(reports,selected,source_manifest=(),read_errors=()):
    key=run_identity(selected)
    if key is None:raise ValueError(_tr('Dungeon-Zuordnung noch nicht erkannt.'))
    unique={}
    for report in reports:
        for fight in report.get('fights',[]):
            candidate={**report,'fights':[fight]}
            if run_identity(candidate)!=key:continue
            unique[(report.get('session',{}).get('id'),str(fight.get('id')))]=deepcopy(fight)
    if not unique:raise ValueError(_tr('Keine erfassten Kämpfe für diese Dungeon-Zuordnung.'))
    fights=sorted(unique.values(),key=lambda f:(f.get('start_ms',0),str(f.get('id'))))
    from .encounter_scope import encounter_kind
    groups={key:[f['id'] for f in fights if encounter_kind(f)==key] for key in ('boss','trash','mixed','unknown')}
    return {'schema':1,'export_type':'recorded_dungeon','exported_utc':datetime.now(timezone.utc).isoformat(),
            'dungeon':{'name':key[3],'map_id':key[2],'run_key':key[1],'session_id':key[0],
                       'scope':'manual_partition' if selected['fights'][-1].get('run_assignment')=='manual' else 'local_connection_and_map_sequence','physical_instance_confirmed':False},
            'session':deepcopy(selected.get('session',{})), 'fights':fights,'encounter_groups':groups,
            'coverage':{'recorded_only':True,'completeness_confirmed':False,'fight_count':len(fights),
                        'partial_fights':sum(bool(f.get('partial') or f.get('coverage_incomplete')) for f in fights),
                        'conflicted_fights':sum(f.get('integrity','ok')!='ok' for f in fights),
                        'active_fights':sum(f.get('reason')=='active' for f in fights),
                        'note':_tr('Alle gespeicherten Kämpfe dieser lokalen Zuordnung, inklusive Trash und Wiederholungen. Gleiche Map kann mehrere Durchläufe enthalten; fehlende Aufnahmen werden nicht ergänzt.')},
            'source_manifest':list(source_manifest),'read_errors':list(read_errors)}

def load_dungeon_log(directory,current,selected):
    from .catalog_evidence import load_fights
    from .encounter_history import EncounterAnnotations
    annotations=EncounterAnnotations(directory)
    docs,errors,manifest=load_fights(directory)
    reports=[annotations.apply({'session':d['session'],'fights':[d['fight']]}) for d in docs]
    # Fresh in-memory frames take precedence over their saved snapshots.
    reports.append(annotations.apply(current));selected=annotations.apply(selected)
    result=dungeon_log(reports,selected,read_errors=errors)
    paths={d['path'] for d in docs if run_identity(annotations.apply({'session':d['session'],'fights':[d['fight']]}))==run_identity(selected)}
    result['source_manifest']=[m for m in manifest if m['path'] in paths]
    result['source_records']=[{'path':d['path'],'sha256':d['sha256'],'record':deepcopy(d['record'])} for d in docs if d['path'] in paths]
    return result

def serialized_log(document):return json.dumps(document,ensure_ascii=False,indent=2,allow_nan=False)+'\n'

def save_log(document,path):
    from uuid import uuid4
    path=Path(path)
    if path.suffix.lower()!='.json':path=path.with_suffix('.json')
    # Do not overwrite input logs even when explicitly selected by accident.
    if path.name.startswith('combat_') or any(path.resolve()==Path(m['path']).resolve() for m in document.get('source_manifest',[])):
        raise ValueError(_tr('Bitte eine neue Exportdatei wählen; Original-Kampflogs bleiben unverändert.'))
    temporary=path.with_name('.'+path.name+'.'+uuid4().hex+'.tmp')
    try:temporary.write_text(serialized_log(document),encoding='utf-8');temporary.replace(path)
    finally:
        if temporary.exists():temporary.unlink()
    return path
