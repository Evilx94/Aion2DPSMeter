"""Atomic per-fight logs, including an updated live snapshot and final closure."""
from .language import tr as _tr
from pathlib import Path
from datetime import datetime
from threading import RLock
from uuid import uuid4
import hashlib,json

class CombatLogWriter:
    def __init__(self,directory):
        self.directory=Path(directory);self.cache={};self.lock=RLock();self.last_path=None
    def save(self,report,force=False):
        from .personal_boss import personal_report
        report=personal_report(report)
        session=report.get('session',{})
        if session.get('mode')!='live' or not session.get('id') or not report.get('packets'):return []
        written=[]
        with self.lock:
            for fight in report.get('fights',[]):
                identifier=fight.get('id',str(fight['start_ms']));key=(session['id'],identifier)
                identity=fight.get('self_identity',report.get('self_identity',{}))
                # Revisions are for stale-writer protection; unchanged closed
                # fights do not get rewritten on every snapshot tick.
                signature=json.dumps([fight,identity],sort_keys=True,ensure_ascii=False)
                if self.cache.get(key)==signature:continue
                suffix=hashlib.sha256(str(identifier).encode()).hexdigest()[:10]
                stamp=datetime.fromtimestamp(fight['start_ms']/1000).strftime('%Y%m%d_%H%M%S')
                path=self.directory/f'combat_{stamp}_{session["id"]}_{suffix}.json'
                record={'schema':1,'session':session,'self_identity':identity,'fight':fight}
                self.directory.mkdir(parents=True,exist_ok=True)
                if path.exists():
                    existing=json.loads(path.read_text(encoding='utf-8'))
                    if existing.get('session',{}).get('id')!=session['id'] or existing.get('fight',{}).get('id')!=fight.get('id'):
                        raise OSError(_tr('Vorhandene Logdatei gehört zu einer anderen Sitzung: ')+str(path))
                    if existing.get('session',{}).get('revision',0)>session.get('revision',0):continue
                temporary=path.with_name('.'+path.name+'.'+uuid4().hex+'.tmp')
                try:
                    temporary.write_text(json.dumps(record,indent=2,ensure_ascii=False),encoding='utf-8');temporary.replace(path)
                finally:
                    if temporary.exists():temporary.unlink()
                self.cache[key]=signature;self.last_path=path;written.append(path)
            # UI/core retain at most 30 completed fights; bound the log cache too.
            if len(self.cache)>256:
                for key in list(self.cache)[:-128]:self.cache.pop(key,None)
        return written
