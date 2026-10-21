"""Opt-in local diagnostic ZIP; no uploads, PCAPs or unfiltered preferences."""
from .language import tr as _tr
from copy import deepcopy
from pathlib import Path
from importlib.metadata import version,PackageNotFoundError
import hashlib,json,platform,re,sys,zipfile
from uuid import uuid4

SAFE_SETTINGS=('display_metric','palette','opacity','overlay','graph_overlay','attachment_mode','click_through','save_combat','save_packets','save_debug','dps_size','graph_size','dps_locked','graph_locked','dps_font_size','track_pvp','archive_combat_days','archive_capture_days')

def encoded(doc):return (json.dumps(doc,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8')

def redactor(report):
    names=set()
    for f in report.get('fights',[]):
        names.update(a.get('name') for a in f.get('actors',[]) if a.get('name'))
        if f.get('self_identity',{}).get('name'):names.add(f['self_identity']['name'])
    if report.get('self_identity',{}).get('name'):names.add(report['self_identity']['name'])
    aliases={name:_tr('<Spieler {0}>' ,i) for i,name in enumerate(sorted(names),1)}
    def redact(text):
        for name,alias in sorted(aliases.items(),key=lambda pair:len(pair[0]),reverse=True):text=re.sub(r'(?<!\w)'+re.escape(name)+r'(?!\w)',alias,text)
        text=re.sub(r'(?:[A-Za-z]:[\\/]|\\\\)[^\r\n\t"<>]*',_tr('<Pfad>'),text)
        text=re.sub(r'\b(?:\d{1,3}\.){3}\d{1,3}\b','<IP>',text)
        text=re.sub(r'NPF_\{[^}]+\}','<Adapter>',text)
        text=re.sub(r'\b[0-9A-Fa-f]{8}(?:-[0-9A-Fa-f]{4}){3}-[0-9A-Fa-f]{12}\b',_tr('<Kennung>'),text)
        return text
    return redact

def fight_summary(fight,redact):
    from .quality import player_quality
    ids={a['id']:i for i,a in enumerate(fight.get('actors',[]),1)}
    fields=('seconds','healing_seconds','total_damage','dps','total_healing','hps','reason','integrity','partial','group_state','group_coverage_confirmed','damage_coverage','healing_coverage_incomplete','map_id','boss_template','boss_type')
    result={k:deepcopy(fight[k]) for k in fields if k in fight}
    result['actors']=[]
    for a in fight.get('actors',[]):
        row={k:a[k] for k in ('class','damage','healing','self_healing','other_healing','hps','dps','hits','crits','casts') if k in a}
        row.update(id=ids[a['id']],name=_tr('Spieler {0}' ,ids[a['id']]),quality=player_quality(a,fight));result['actors'].append(row)
    result['skills']=[{**{k:r[k] for k in ('skill','damage','healing','self_healing','other_healing','unclassified_recovery','casts','hits','crits','dot_ticks') if k in r},'actor':ids[r['actor']]} for r in fight.get('skills',[]) if r.get('actor') in ids]
    return json.loads(redact(encoded(result).decode('utf-8')))

def build_bundle(report,settings,sections=('counters','settings'),log_directory=None):
    allowed={'counters','settings','fight','errors'}
    if not set(sections)<=allowed:raise ValueError('Unbekannte Diagnose-Auswahl')
    redact=redactor(report);packages={}
    for name in ('scapy','PySide6'):
        try:packages[name]=version(name)
        except PackageNotFoundError:packages[name]=_tr('nicht ermittelt')
    files={'overview.json':encoded({'schema':1,'application':'Aion2Meter','build':'Entwicklung','python':sys.version.split()[0],'system':platform.system(),'system_release':platform.release(),'packages':packages,'selected_sections':sorted(sections),'worldboss_open_world':_tr('offen / nicht vollständig bestätigt'),'no_raw_capture':True,'no_upload':True})}
    overview=json.loads(files['overview.json']);base=Path(__file__).parent
    overview['source_sha256']={name:hashlib.sha256((base/name).read_bytes()).hexdigest() for name in ('core/parser.py','core/combat.py','core/transport.py','quality.py','support_export.py') if (base/name).is_file()};files['overview.json']=encoded(overview)
    if 'settings' in sections:files['settings.json']=redact(encoded({k:settings[k] for k in SAFE_SETTINGS if k in settings}).decode('utf-8')).encode('utf-8')
    if 'counters' in sections:
        fields=('network','transport','framing','parser_errors','decisions','group_state','party_trusted','coverage_incomplete')
        counters={k:report[k] for k in fields if k in report};files['counters.json']=redact(encoded(counters).decode('utf-8')).encode('utf-8')
    if 'fight' in sections and report.get('fights'):files['fight.json']=encoded(fight_summary(report['fights'][-1],redact))
    if 'errors' in sections and log_directory:
        root=Path(log_directory).resolve()
        paths=sorted(root.glob('meter_*.log'),key=lambda p:p.stat().st_mtime,reverse=True)[:3]
        for i,path in enumerate(paths,1):
            if path.is_symlink() or root not in path.resolve().parents:continue
            with path.open('rb') as source:
                source.seek(max(0,path.stat().st_size-65536));tail=source.read(65536)
            files[f'errors/log-{i}.txt']=redact(tail.decode('utf-8',errors='replace')).encode('utf-8')
    files['manifest.json']=encoded({'sha256':{name:hashlib.sha256(data).hexdigest() for name,data in files.items()},'note':_tr('Spielernamen aus dem aktuellen Report werden ersetzt. Optionale Fehlertexte können weitere personenbezogene Angaben enthalten. Keine Rohmitschnitte enthalten.')})
    return files

def save_bundle(files,path):
    path=Path(path).with_suffix('.zip');temp=path.with_name('.'+uuid4().hex+'.tmp')
    if any(name.startswith(('/','\\')) or '..' in Path(name).parts or ':' in name for name in files):raise ValueError(_tr('Ungültiger ZIP-Eintrag'))
    try:
        with zipfile.ZipFile(temp,'w',compression=zipfile.ZIP_DEFLATED) as archive:
            for name,data in files.items():archive.writestr(name,data)
        temp.replace(path)
    finally:
        if temp.exists():temp.unlink()
    return path
