"""Search metadata and reversible, explicitly requested age-based archiving."""
from .language import tr as _tr
from datetime import datetime
from pathlib import Path
import json,time
from uuid import uuid4
from .catalog_evidence import validate_fight

def inside(path,root):
    root=Path(root).resolve();path=Path(path)
    return not path.is_symlink() and root in path.resolve().parents

def read_record(path):
    path=Path(path)
    if path.stat().st_size>16*1024*1024:raise ValueError(_tr('Kampflog größer als 16 MiB'))
    doc=json.loads(path.read_text(encoding='utf-8-sig'));validate_fight(doc['fight'])
    if not doc.get('session',{}).get('id'):raise ValueError(_tr('Sitzungskennung fehlt'))
    return doc

def scan_logs(directory,include_archive=False,cancel=None):
    root=Path(directory);paths=list(root.glob('combat_*.json'))
    if include_archive and (root/'.archive').exists():paths.extend((root/'.archive').rglob('combat_*.json'))
    records={};errors=[];physical_files=0;total_bytes=0
    from .encounter_history import EncounterAnnotations,OUTCOMES,outcome
    try:marks={(r['session'],r['fight']):r.get('outcome','') for r in EncounterAnnotations(root).read()}
    except (OSError,ValueError) as error:marks={};errors.append({'file':'encounter_annotations.json','error':str(error)})
    for path in sorted(paths):
        if cancel is not None and cancel.is_set():break
        if not inside(path,root):continue
        try:
            stat=path.stat();physical_files+=1;total_bytes+=stat.st_size;doc=read_record(path);f=doc['fight'];s=doc['session']
            rank=(bool(doc.get('metadata_correction')) or path.name.startswith('combat_corrected_'),f.get('reason')!='active',s.get('revision',0),path.name)
            key=str(s['id']),str(f['id'])
            people=sorted({str(a.get('name','')) for a in f.get('actors',[]) if a.get('name')})
            own=doc.get('self_identity',f.get('self_identity',{})).get('name','')
            item={'key':key,'path':str(path),'size':stat.st_size,'start_ms':f.get('start_ms',0),'boss':f.get('boss_name') or f.get('target_name') or _tr('Kampf'),'area':f.get('dungeon_name') or f.get('region_name') or f.get('map_name') or '', 'people':people,'character':own,'reason':f.get('reason',''),'rank':rank,'archived':'.archive' in path.relative_to(root).parts}
            item['outcome']=OUTCOMES[marks[key]] if marks.get(key) else outcome(f)
            if key not in records or rank>records[key]['rank']:records[key]=item
        except (OSError,ValueError,KeyError,TypeError) as error:errors.append({'file':path.name,'error':str(error)})
    return {'records':sorted(records.values(),key=lambda r:r['start_ms'],reverse=True),'errors':errors,'physical_files':physical_files,'bytes':total_bytes}

def filter_records(records,boss='',character='',area='',from_ms=None,to_ms=None):
    result=[]
    for r in records:
        if boss.casefold() not in r['boss'].casefold():continue
        if character.casefold() not in ' '.join([r['character'],*r['people']]).casefold():continue
        if area.casefold() not in r['area'].casefold():continue
        if from_ms is not None and r['start_ms']<from_ms:continue
        if to_ms is not None and r['start_ms']>=to_ms:continue
        result.append(r)
    return result

def storage_size(directory,pattern):
    count=size=0
    for path in Path(directory).glob(pattern):
        try:
            if inside(path,directory) and path.is_file():count+=1;size+=path.stat().st_size
        except OSError:continue
    return count,size

def archive_candidates(log_directory,capture_directory,combat_days=0,capture_days=0,protected_sessions=(),protected_paths=(),now=None):
    now=time.time() if now is None else now;protected={str(Path(p).resolve()) for p in protected_paths if p};result=[]
    for root,pattern,days,kind in ((Path(log_directory),'combat_*.json',combat_days,'Kampflog'),(Path(capture_directory),'live_*.pcap',capture_days,'Mitschnitt')):
        if days<=0:continue
        for path in root.glob(pattern):
            if not inside(path,root) or str(path.resolve()) in protected:continue
            try:
                st=path.stat()
                if st.st_mtime>=now-days*86400:continue
                if kind=='Kampflog':
                    doc=read_record(path)
                    if doc['fight'].get('reason')=='active' or doc['session']['id'] in protected_sessions:continue
                result.append({'path':str(path.resolve()),'root':str(root.resolve()),'size':st.st_size,'mtime_ns':st.st_mtime_ns,'kind':kind})
            except (OSError,ValueError,KeyError,TypeError):continue
    return result

def archive_files(plan):
    moved=[];errors=[]
    for item in plan:
        source=Path(item['path']);root=Path(item['root'])
        try:
            if not inside(source,root) or source.parent!=root.resolve():raise ValueError(_tr('Datei liegt nicht direkt im vorgesehenen Ordner'))
            stat=source.stat()
            if (stat.st_size,stat.st_mtime_ns)!=(item['size'],item['mtime_ns']):raise ValueError(_tr('Datei wurde seit der Vorschau verändert'))
            target=root/'.archive'/datetime.now().strftime('%Y%m%d')/source.name
            if not inside(target,root):raise ValueError(_tr('Archivziel außerhalb des Ordners'))
            target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists():target=target.with_name(target.stem+'_'+uuid4().hex[:8]+target.suffix)
            source.rename(target);moved.append(str(target))
        except (OSError,ValueError) as error:errors.append({'file':source.name,'error':str(error)})
    return {'moved':moved,'errors':errors}

def restore_file(path,root):
    path=Path(path);root=Path(root).resolve()
    if not inside(path,root) or '.archive' not in path.relative_to(root).parts:raise ValueError(_tr('Kein Archiv-Eintrag dieses Ordners'))
    target=root/path.name
    if target.exists():raise ValueError(_tr('Datei gleichen Namens existiert bereits; nichts überschrieben'))
    path.rename(target);return target

def report_from_file(path,directory):
    from .encounter_history import EncounterAnnotations
    if not inside(path,directory):raise ValueError(_tr('Log liegt außerhalb des gewählten Ordners'))
    d=read_record(path)
    return EncounterAnnotations(directory).apply({'session':d['session'],'self_identity':d.get('self_identity',{}),'self_id':d.get('self_identity',{}).get('id'),'fights':[d['fight']]})
