"""User annotations stay separate from immutable combat logs and protocol facts."""
from .language import tr as _tr
from copy import deepcopy
from pathlib import Path
import json
from uuid import uuid4

from .language import TranslatedDict
OUTCOMES=TranslatedDict({'':'Automatisch','kill':'Kill (manuell)','wipe':'Wipe (manuell)','reset':'Reset (manuell)','phase':'Phase (manuell)'})

def outcome(fight):
    manual=fight.get('manual_outcome')
    if manual in OUTCOMES and manual:return OUTCOMES[manual]
    return {'target_death':_tr('Tod bestätigt'),'target_reset':_tr('Boss-Reset'),'active':_tr('Läuft')}.get(fight.get('reason'),_tr('Ende unbestätigt'))

def fight_key(report,fight):return str(report.get('session',{}).get('id','')),str(fight.get('id',''))

class EncounterAnnotations:
    def __init__(self,directory):self.path=Path(directory)/'encounter_annotations.json'
    def read(self):
        if not self.path.exists():return []
        doc=json.loads(self.path.read_text(encoding='utf-8'))
        if not isinstance(doc,dict) or doc.get('schema')!=1 or not isinstance(doc.get('records'),list):raise ValueError(_tr('Ungültige Verlaufsmarkierungen'))
        if any(not isinstance(r,dict) or not isinstance(r.get('session'),str) or not isinstance(r.get('fight'),str) or type(r.get('start_ms')) is not int or r.get('outcome','') not in OUTCOMES or type(r.get('run_start',False)) is not bool for r in doc['records']):raise ValueError(_tr('Ungültige Verlaufsmarkierung'))
        return doc['records']
    def write(self,report,**changes):
        fight=report['fights'][-1];key=fight_key(report,fight)
        rows=self.read();record=next((r for r in rows if (r.get('session'),r.get('fight'))==key),None)
        if record is None:
            record={'session':key[0],'fight':key[1],'base_run':fight.get('original_run_key',fight.get('run_key')),'map_id':fight.get('map_id'),'dungeon_name':fight.get('dungeon_name'),'start_ms':fight['start_ms']};rows.append(record)
        if 'outcome' in changes and changes['outcome'] not in OUTCOMES:raise ValueError(_tr('Unbekanntes Ergebnis'))
        record.update(changes)
        self.path.parent.mkdir(parents=True,exist_ok=True);temp=self.path.with_name('.'+uuid4().hex+'.tmp')
        try:temp.write_text(json.dumps({'schema':1,'records':rows},ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(self.path)
        finally:
            if temp.exists():temp.unlink()
    def apply(self,report):
        result=deepcopy(report);rows=self.read()
        for f in result.get('fights',[]):
            session,identifier=fight_key(result,f);base=f.get('original_run_key',f.get('run_key'))
            own=next((r for r in rows if (r.get('session'),r.get('fight'))==(session,identifier)),{})
            f.pop('manual_outcome',None);f.pop('manual_run_start',None)
            if own.get('outcome') in OUTCOMES and own.get('outcome'):f['manual_outcome']=own['outcome']
            if own.get('run_start'):f['manual_run_start']=True
            boundaries=[r for r in rows if r.get('session')==session and r.get('base_run')==base and base is not None and r.get('map_id')==f.get('map_id') and r.get('dungeon_name')==f.get('dungeon_name') and r.get('run_start') and type(r.get('start_ms')) is int and r['start_ms']<=f.get('start_ms',0)]
            if boundaries:
                boundary=max(boundaries,key=lambda r:(r['start_ms'],r['fight']))
                f['original_run_key']=base;f['run_key']=f"{base}:manual:{boundary['fight']}";f['run_assignment']='manual'
            elif 'original_run_key' in f:f['run_key']=base;f.pop('original_run_key',None);f.pop('run_assignment',None)
        return result
