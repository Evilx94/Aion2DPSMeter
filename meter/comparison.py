"""Compare observed encounters without joining players by transient entity ID."""
from .language import tr as _tr
from collections import Counter
from copy import deepcopy
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QComboBox,QLabel,QTableWidget,QTableWidgetItem,QTabWidget,QHeaderView
from .overlay import number
from .core.skill_labels import SkillLabels,label_row

def comparable(left,right):
    if not left.get('fights') or not right.get('fights'):return False
    a=left['fights'][-1];b=right['fights'][-1]
    same=(left.get('session',{}).get('id'),a.get('id'))==(right.get('session',{}).get('id'),b.get('id'))
    return bool(not same and a.get('boss_template') and a['boss_template']==b.get('boss_template') and a.get('map_id') is not None and a['map_id']==b.get('map_id'))

def actor_key(actor,fight):
    character=actor.get('equipment_character_id')
    if type(character) is int and character>0:return ('character',character)
    server=actor.get('server',0)
    own=fight.get('self_identity',{})
    if not server and actor.get('id')==own.get('id'):server=own.get('server',0)
    if actor.get('name') and server and actor.get('class'):return ('identity',actor['name'].casefold(),server,actor['class'])
    return None

def pairs(left,right):
    a=left['fights'][-1];b=right['fights'][-1];la=a.get('actors',[]);lb=b.get('actors',[])
    ka=[actor_key(p,a) for p in la];kb=[actor_key(p,b) for p in lb];ca=Counter(ka);cb=Counter(kb);used=set();result=[]
    for player,key in zip(la,ka):
        target=kb.index(key) if key is not None and ca[key]==1 and cb[key]==1 else None
        other=lb[target] if target is not None else None
        if target is not None:used.add(target)
        result.append((player,other))
    result.extend((None,p) for i,p in enumerate(lb) if i not in used)
    return result

def rate(actor,fight,kind):
    if actor is None or fight.get('integrity','ok')!='ok':return None
    from .healing import observed_amount
    value=actor.get('damage') if kind=='damage' else observed_amount(fight,actor)
    if value is None:return None
    seconds=max(1,fight.get('seconds',1) if kind=='damage' else fight.get('healing_seconds',fight.get('seconds',1)))
    return value/seconds

def delta(left,right):return None if left is None or right is None else right-left

def table(headers):
    widget=QTableWidget();widget.setColumnCount(len(headers));widget.setHorizontalHeaderLabels(headers)
    widget.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers);widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents);widget.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch)
    return widget

def fill(widget,rows):
    widget.setRowCount(len(rows))
    for i,row in enumerate(rows):
        for j,value in enumerate(row):widget.setItem(i,j,QTableWidgetItem(str(value)))

class FightComparison(QDialog):
    def __init__(self,selected,reports,parent=None):
        super().__init__(parent);self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose);self.setWindowTitle(_tr('Bosskämpfe vergleichen'));self.resize(1000,690)
        self.setStyleSheet('QDialog,QLabel,QWidget {background:#101b24;color:#dce9f2;} QComboBox {background:#243b49;padding:5px;} QTableWidget {background:#13212b;color:#dce9f2;gridline-color:#304754;} QHeaderView::section {background:#243b49;color:#dce9f2;padding:4px;} QTabBar::tab {background:#243b49;color:#dce9f2;padding:6px;}')
        self.left=deepcopy(selected);self.candidates=[deepcopy(r) for r in reports if comparable(selected,r)]
        self.labels=getattr(parent,'skill_labels',SkillLabels.builtin())
        layout=QVBoxLayout(self);self.choice=QComboBox();layout.addWidget(self.choice)
        from datetime import datetime
        for r in self.candidates:
            f=r['fights'][-1];self.choice.addItem(datetime.fromtimestamp(f['start_ms']/1000).strftime('%d.%m. %H:%M:%S')+f" · {int(f.get('seconds',0))} s")
        self.notice=QLabel();self.notice.setWordWrap(True);layout.addWidget(self.notice)
        self.players=table([_tr('Spieler'),'DPS A','DPS B','Δ DPS','HPS A','HPS B','Δ HPS']);layout.addWidget(self.players)
        controls=QHBoxLayout();self.player=QComboBox();controls.addWidget(self.player,1);self.metric_choice=QComboBox();self.metric_choice.addItem(_tr('Schaden'),'damage');self.metric_choice.addItem(_tr('Heilung'),'healing');controls.addWidget(self.metric_choice);layout.addLayout(controls)
        tabs=QTabWidget();self.skills=table([_tr('Fähigkeit'),_tr('Menge A'),_tr('Menge B'),'/s A','/s B',_tr('Casts A'),_tr('Casts B')]);tabs.addTab(self.skills,_tr('Fähigkeiten'))
        self.charges=table([_tr('Basisfähigkeit'),_tr('Casts A'),_tr('Casts B'),'Charge 1/2/MAX A','Charge 1/2/MAX B']);tabs.addTab(self.charges,_tr('Casts / Charge'))
        self.buffs=table(['Buff / Debuff','Uptime A','Uptime B']);tabs.addTab(self.buffs,'Buff-Uptime');layout.addWidget(tabs,2)
        self.choice.currentIndexChanged.connect(self.render);self.player.currentIndexChanged.connect(self.render_player);self.metric_choice.currentIndexChanged.connect(self.render_player);self.render()
    def render(self,*args):
        index=self.choice.currentIndex()
        if not 0<=index<len(self.candidates):self.notice.setText(_tr('Kein zweiter Kampf mit bestätigtem gleichem Boss-Template und gleicher Karte.'));return
        self.right=self.candidates[index];a=self.left['fights'][-1];b=self.right['fights'][-1];self.actor_pairs=pairs(self.left,self.right)
        caution=any(f.get('partial') or f.get('coverage_incomplete') or f.get('group_coverage_confirmed') is False or f.get('integrity','ok')!='ok' for f in (a,b))
        self.notice.setText(f"{a.get('boss_name') or 'Boss'} · A: {a.get('seconds',0):.1f} s · B: {b.get('seconds',0):.1f} s\n"+(_tr('Unvollständige/abweichende Abdeckung: Zahlen nur eingeschränkt vergleichbar. ') if caution else '')+_tr('Verschiedene Kampfdauern und Gruppen sind keine Leistungsbewertung. Nicht sicher zugeordnete Spieler bleiben getrennt; Heilung ist beobachtet, nicht bestätigte effektive Heilung.'))
        rows=[];self.player.blockSignals(True);self.player.clear()
        for note in dict.fromkeys(f.get('scope_note') for f in (a,b) if f.get('scope_note')):self.notice.setText(self.notice.text()+'\n'+note)
        for left,right in self.actor_pairs:
            p=left or right;name=p.get('name') or f"Entity {p.get('id')}"
            if left is None:name+=_tr(' · nur B')
            elif right is None:name+=_tr(' · nur A')
            da,db=rate(left,a,'damage'),rate(right,b,'damage');ha,hb=rate(left,a,'healing'),rate(right,b,'healing')
            rows.append([name,number(da),number(db),number(delta(da,db)),number(ha),number(hb),number(delta(ha,hb))]);self.player.addItem(name)
        self.player.blockSignals(False);fill(self.players,rows);self.render_player()
    def render_player(self,*args):
        index=self.player.currentIndex()
        if not hasattr(self,'actor_pairs') or not 0<=index<len(self.actor_pairs):return
        a=self.left['fights'][-1];b=self.right['fights'][-1];actors=self.actor_pairs[index];kind=self.metric_choice.currentData();maps=[]
        for f,p in zip((a,b),actors):maps.append({r['skill']:r for r in f.get('skills',[]) if p and r['actor']==p['id']})
        rows=[]
        for skill in sorted(set(maps[0])|set(maps[1])):
            from .healing import RECOVERY_EXCLUSIONS
            if kind=='healing' and skill in RECOVERY_EXCLUSIONS:continue
            values=[];counts=[]
            for f,m,p in zip((a,b),maps,actors):
                r=m.get(skill);valid=p is not None and f.get('integrity','ok')=='ok';value=r.get(kind) if r else (0 if valid else None)
                if not valid:value=None
                seconds=max(1,f.get('seconds',1) if kind=='damage' else f.get('healing_seconds',f.get('seconds',1)))
                values.extend([number(value),number(value/seconds) if value is not None else '—']);counts.append(str(r.get('casts','—')) if r and valid else '—')
            name=label_row({'skill':skill},self.labels).get('name') or '?'
            rows.append([f'{name} ({skill})',values[0],values[2],values[1],values[3],*counts])
        fill(self.skills,rows)
        usage=[{r['skill']:r for r in f.get('cast_usage',[]) if p and r['actor']==p['id']} for f,p in zip((a,b),actors)]
        rows=[]
        for skill in sorted(set(usage[0])|set(usage[1])):
            label=label_row({'skill':skill},self.labels).get('name') or '?';counts=[];stages=[]
            for f,m in zip((a,b),usage):
                r=m.get(skill);valid=f.get('integrity','ok')=='ok'
                counts.append(str(r['casts']) if r and valid else '—')
                stages.append('/'.join(str(r['charges'].get(str(i),0)) for i in (1,2,3)) if r and r.get('charges') and valid else '—')
            rows.append([label,*counts,*stages])
        fill(self.charges,rows)
        buffs=[{r['abnormal']:r for r in f.get('buffs',[]) if p and r['actor']==p['id']} for f,p in zip((a,b),actors)]
        rows=[]
        for identifier in sorted(set(buffs[0])|set(buffs[1])):
            label=(buffs[0].get(identifier) or buffs[1][identifier]).get('name') or str(identifier)
            rows.append([label,*[(f"{m[identifier]['uptime_percent']:.1f} %" if identifier in m and f.get('integrity','ok')=='ok' else '—') for m,f in zip(buffs,(a,b))]])
        fill(self.buffs,rows)
