"""Separate player and fight-history views backed only by observed combat data."""
from .language import tr as _tr,decimal
from copy import deepcopy
from pathlib import Path
import json
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QDialog,QWidget,QVBoxLayout,QHBoxLayout,QLabel,QTableWidget,QTableWidgetItem,QHeaderView,QComboBox,QPushButton,QCheckBox,QTabWidget,QFileDialog
from .overlay import DamageView,actor_label,number
from .class_icons import skill_icon
from .core.skill_labels import SkillLabels,label_row
from .equipment import equipment_text
from .export_job import ExportController
from .rune_display import rune_display
SKILL_LABELS=SkillLabels.builtin()

def percentage(amount,total):return (100*amount/total) if total else 0

class PlayerDetails(QDialog):
    def __init__(self,report,actor_id,parent=None):
        super().__init__(parent);self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose);self.actor_id=actor_id;self.report=deepcopy(report);self.skill_labels=getattr(parent,'skill_labels',SKILL_LABELS)
        self.fight_id=self.report['fights'][-1]['id'];self.session_id=report.get('session',{}).get('id');self.setWindowTitle(_tr('Spieler · Kampfanalyse'));self.resize(880,620)
        layout=QVBoxLayout(self);heading=QHBoxLayout();self.title=QLabel();self.title.setStyleSheet('font-size:20pt;font-weight:600;');heading.addWidget(self.title,1);layout.addLayout(heading)
        self.summary=QLabel();self.summary.setWordWrap(True);self.summary.setStyleSheet('padding:12px;background:#20333f;border-radius:6px;');layout.addWidget(self.summary)
        self.quality=QLabel();self.quality.setWordWrap(True);layout.addWidget(self.quality)
        self.table=QTableWidget();self.table.setColumnCount(11);self.table.setHorizontalHeaderLabels([_tr('Fähigkeit'),_tr('Schaden'),_tr('Anteil'),'DPS',_tr('Treffer'),_tr('Krit.'),'DoT-Ticks',_tr('Begleiter'),_tr('Heilung'),_tr('Casts'),_tr('Runen')])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers);self.table.setAlternatingRowColors(True);self.table.setStyleSheet('QTableWidget {background:#13212b;alternate-background-color:#1c303d;color:#dce9f2;gridline-color:#304754;} QHeaderView::section {background:#1b2c36;color:#dce9f2;border:1px solid #304754;padding:4px;} QTableWidget::item:selected {background:#345363;}');self.table.verticalHeader().hide();self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents);self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch);self.tabs=QTabWidget();self.tabs.addTab(self.table,_tr('Schaden'));self.table.setColumnHidden(8,True);self.table.horizontalHeader().moveSection(10,1);heal_page=QWidget();heal_layout=QVBoxLayout(heal_page);self.heal_note=QLabel();self.heal_note.setWordWrap(True);heal_layout.addWidget(self.heal_note);self.heal_table=QTableWidget();self.heal_table.setColumnCount(7);self.heal_table.setHorizontalHeaderLabels([_tr('Fähigkeit'),_tr('Heilung'),_tr('Anteil'),'HPS',_tr('Selbst'),_tr('Andere'),_tr('Runen')]);self.heal_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers);self.heal_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents);self.heal_table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch);self.heal_table.horizontalHeader().moveSection(6,1);self.heal_table.setStyleSheet(self.table.styleSheet());heal_layout.addWidget(self.heal_table);self.tabs.addTab(heal_page,_tr('Heilung'));buff_page=QWidget();buff_layout=QVBoxLayout(buff_page);self.buff_note=QLabel();self.buff_note.setWordWrap(True);buff_layout.addWidget(self.buff_note);self.buff_table=QTableWidget();self.buff_table.setColumnCount(4);self.buff_table.setHorizontalHeaderLabels(['Buff / Debuff',_tr('Aktiv (s)'),'Uptime','Max. Stacks']);self.buff_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers);self.buff_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents);self.buff_table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch);buff_layout.addWidget(self.buff_table);self.tabs.addTab(buff_page,'Buffs / Debuffs');cast_page=QWidget();cast_layout=QVBoxLayout(cast_page);self.cast_note=QLabel();self.cast_note.setWordWrap(True);cast_layout.addWidget(self.cast_note);self.cast_table=QTableWidget();self.cast_table.setColumnCount(6);self.cast_table.setHorizontalHeaderLabels([_tr('Fähigkeit'),_tr('Casts'),'Charge 1','Charge 2','MAX',_tr('Weitere')]);self.cast_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers);self.cast_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents);self.cast_table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch);cast_layout.addWidget(self.cast_table);self.tabs.addTab(cast_page,_tr('Casts / Trigger'));layout.addWidget(self.tabs,2)
        self.graph=DamageView(True);self.graph.setMinimumHeight(140);layout.addWidget(self.graph,1);self.tabs.currentChanged.connect(self.update_graph)
        self.table.horizontalHeaderItem(9).setToolTip(_tr('Server-Castmeldungen dieser Variante, auch automatische Auslösungen; Gesamt pro Basisfähigkeit im Tab Casts / Trigger. Treffer und Begleiter-Angriffe werden nicht als Spieler-Casts gezählt.'))
        self.buff_table.setStyleSheet(self.table.styleSheet());self.cast_table.setStyleSheet(self.table.styleSheet())
        self.tabs.setStyleSheet('QTabBar::tab {background:#243b49;color:#dce9f2;padding:7px 12px;} QTabBar::tab:selected {background:#345363;color:#71ddc4;}')
        note=QLabel(_tr('Graph: gesamter beobachteter Kampf. Skill-ID, Quelle und Variantenstatus stehen im Tooltip. DoT- und Begleiterschaden sind Teil des Gesamtschadens.'));note.setWordWrap(True);layout.addWidget(note)
        self.rune_note=QLabel(_tr('Runen: * abgeleitet, nicht einzeln bestätigt. — keine belastbare Zuordnung.'));self.rune_note.setWordWrap(True);layout.addWidget(self.rune_note)
        self.set_report(report)
    def set_rune_cell(self,table,index,column,row):
        value,explanation,status=rune_display(row)
        item=QTableWidgetItem(value);item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item.setToolTip(_tr('Skill-ID: {0}',row['skill'])+'\n'+explanation)
        if status!='unknown':item.setForeground(QColor('#71ddc4' if status in ('confirmed_exact','user_confirmed_pattern') else '#d9bd7b'))
        table.setItem(index,column,item)
    def set_report(self,report):
        from .personal_boss import personal_report
        report=personal_report(report)
        if report.get('session',{}).get('id')!=self.session_id:return
        fight=next((f for f in report.get('fights',[]) if f['id']==self.fight_id),None)
        if fight is None:return
        actor=next((a for a in fight.get('actors',[]) if a['id']==self.actor_id),None)
        if actor is None:return
        self.report=deepcopy({**report,'fights':[fight]});self.title.setText(actor_label(actor,fight,report)+' · '+(actor.get('class') or _tr('Klasse unbekannt')));self.title.setTextFormat(Qt.TextFormat.PlainText)
        valid=fight.get('integrity','ok')=='ok';damage=actor.get('damage',0);total=fight.get('total_damage') or 0
        from .observation_quality import sparse_damage_coverage,damage_amount_partial
        share=decimal(f'{percentage(damage, total):.1f} %') if valid and fight.get('tracking_scope')!='self' and not sparse_damage_coverage(fight) else '—'
        self.summary.setText(_tr('{0} DPS · {1} Schaden · {2} Anteil\n{3} Treffer · {4} kritisch · {5} DoT-Ticks · {6} Begleiter · {7} Heilung' ,number(actor.get('dps') if valid else None),number(damage),share,actor.get('hits', 0),actor.get('crits', 0),actor.get('dot_ticks', 0),number(actor.get('summon_damage', 0)),number(actor.get('healing', 0))))
        from .observation_quality import damage_amount_missing
        if damage_amount_missing(actor,fight):
            self.summary.setText(_tr('Kein Schadensbetrag erfasst; 0 Schaden ist nicht bestätigt.')+'\n'+_tr('{0} Casts / Trigger · {1} Heilung',actor.get('casts',0),number(actor.get('healing',0))))
        if damage_amount_partial(actor,fight):self.summary.setText(self.summary.text()+'\n'+_tr('Nur periodische Schadensbeträge erfasst; direkte Treffer fehlen.'))
        self.summary.setText(self.summary.text()+'\n'+equipment_text(actor))
        self.damage_summary=self.summary.text()
        self.quality.setText(_tr('Paketkonflikt: Zahlen sind nicht verlässlich.') if not valid else (_tr('Teilausschnitt / unvollständige Zuordnung – nur beobachtete Ereignisse.') if fight.get('partial') or fight.get('coverage_incomplete') else _tr('Beobachtete Kampfdaten')))
        from .quality import quality_text
        self.quality.setText(quality_text(actor,fight))
        if fight.get('scope_note'):self.quality.setText(self.quality.text()+'\n'+fight['scope_note'])
        skills=sorted((row for row in fight.get('skills',[]) if row['actor']==self.actor_id and row.get('damage',0)>0),key=lambda row:row['damage'],reverse=True)
        self.table.setRowCount(len(skills));seconds=max(1,fight.get('seconds',1))
        for i,row in enumerate(skills):
            row=label_row(dict(row),self.skill_labels)
            display_name=row.get('name') or '?'
            if row.get('charge_level') and row.get('name')=='Bolt':display_name=row['name']+' · '+('MAX' if row['charge_level']==3 else 'Charge '+str(row['charge_level']))
            values=[display_name,number(row['damage']),decimal(f"{percentage(row['damage'], damage):.1f} %") if valid else '—',number(row['damage']/seconds) if valid else '—',str(row.get('hits','—')),str(row.get('crits','—')),str(row.get('dot_ticks','—')),number(row['summon_damage']) if 'summon_damage' in row else '—',number(row['healing']) if 'healing' in row else '—',str(row['casts']) if valid and 'casts' in row else '—']
            for j,value in enumerate(values):
                item=QTableWidgetItem(value);item.setTextAlignment(Qt.AlignmentFlag.AlignLeft if j==0 else Qt.AlignmentFlag.AlignRight);self.table.setItem(i,j,item)
                if j==0:
                    item.setIcon(skill_icon(row.get('icon_skill',row['skill'])));item.setToolTip(_tr('Skill-ID: {0}\nQuelle: {1}' ,row['skill'],row.get('name_source', 'nicht zugeordnet'))+('\n'+_tr('Bekannter Basisname; genauer Untereffekt nicht zugeordnet.') if row.get('name_match')=='family_parent' else '')+'\n'+_tr('Runen')+': '+rune_display(row)[0]+'\n'+rune_display(row)[1])
            self.set_rune_cell(self.table,i,10,row)
        from .healing import RECOVERY_EXCLUSIONS,observed_amount
        heals=sorted((r for r in fight.get('skills',[]) if r['actor']==self.actor_id and r.get('healing',0)>0 and r['skill'] not in RECOVERY_EXCLUSIONS),key=lambda r:r['healing'],reverse=True)
        self.heal_note.setText(_tr('Beobachtete Protokollheilung; effektive Heilung und Überheilung sind unbestätigt. Fremdheilung umfasst andere Entities. Die ungeklärte Regeneration 16990004 ist ausgenommen, ohne sie als HP oder MP zu benennen.')+(_tr(' Älterer Log: Selbst-/Fremdaufteilung unbekannt.') if not fight.get('healing_observed') else ''))
        self.heal_table.setRowCount(len(heals));heal_seconds=max(1,fight.get('healing_seconds',fight.get('seconds',1)))
        for index,record in enumerate(heals):
            row=label_row(dict(record),self.skill_labels);amount=row['healing']
            values=[row.get('name') or '?',number(amount) if valid else '—',decimal(f'{percentage(amount, observed_amount(fight, actor) or 0):.1f} %') if valid else '—',number(amount/heal_seconds) if valid else '—',number(row.get('self_healing')) if valid else '—',number(row.get('other_healing')) if valid else '—']
            for column,value in enumerate(values):
                item=QTableWidgetItem(value);self.heal_table.setItem(index,column,item)
                if column==0:item.setToolTip(_tr('Skill-ID: {0}\nQuelle: {1}' ,row['skill'],row.get('name_source', 'nicht zugeordnet')))
            self.set_rune_cell(self.heal_table,index,6,row)
        self.rune_note.setVisible(any(table.item(i,column) and table.item(i,column).text().endswith(' *') for table,column in ((self.table,10),(self.heal_table,6)) for i in range(table.rowCount())))
        usage=sorted((row for row in fight.get('cast_usage',[]) if row['actor']==self.actor_id),key=lambda row:row['casts'],reverse=True)
        self.cast_note.setText(_tr('Server-Castmeldungen pro Basisfähigkeit, einschließlich automatischer Auslösungen. Unabhängig von Trefferzahl; Begleiter-Angriffe sind ausgeschlossen. Erste Angriffs-Casts bis 1 s vor dem ersten Schaden sind enthalten; abgebrochene Casts können enthalten sein.') if 'cast_usage' in fight else _tr('Dieser ältere Log enthält noch keine Cast-Zählung; Treffer werden nicht in Casts umgerechnet.'))
        self.cast_table.setRowCount(len(usage))
        for index,record in enumerate(usage):
            row=label_row(dict(record),self.skill_labels);charges=row.get('charges',{})
            values=[row.get('name') or '?',str(row['casts']) if valid else '—']+[str(charges.get(str(level),0)) if valid and row['skill']==17060000 else '—' for level in (1,2,3)]+[str(row['casts']-sum(charges.values())) if valid and row['skill']==17060000 else '—']
            for column,value in enumerate(values):
                item=QTableWidgetItem(value);self.cast_table.setItem(index,column,item)
                if column==0:item.setToolTip(_tr('Basis-ID: ')+str(row['skill'])+_tr('\nErfasste Varianten: ')+', '.join(str(v['skill']) for v in row.get('variants',[])))
        buffs=[row for row in fight.get('buffs',[]) if row['actor']==self.actor_id]
        self.buff_note.setText(_tr('Beobachtete Uptime; beim Aufnahmestart bereits laufende Buffs können fehlen. Keine Berechnung zusätzlichen Buff-Schadens.') if 'buffs' in fight else _tr('Dieser ältere Log enthält noch keine Buff-Auswertung.'))
        if not buffs and 'buffs' in fight:self.buff_note.setText(_tr('Keine messbaren Buffintervalle für diesen Spieler. Das bedeutet keine bestätigte Uptime von 0 %.'))
        self.buff_table.setRowCount(len(buffs))
        for index,buff in enumerate(buffs):
            from .core.skill_labels import label_buff_row
            buff=label_buff_row(dict(buff),self.skill_labels)
            values=[buff.get('name') or '?',decimal(f"{buff['uptime_ms'] / 1000:.1f}") if valid else '—',decimal(f"{buff['uptime_percent']:.1f} %") if valid else '—',str(buff['max_stacks']) if valid else '—']
            for column,value in enumerate(values):
                item=QTableWidgetItem(value);self.buff_table.setItem(index,column,item)
                if column==0:item.setToolTip(_tr('Buff-ID: {0}\nQuelle: {1}\nNur beobachtete Zeitintervalle.' ,buff['abnormal'],buff.get('name_source', 'nicht zugeordnet')))
        self.update_graph()
    def update_graph(self,*args):
        healing=self.tabs.currentIndex()==1
        self.graph.set_data(self.report,{'display_metric':'healing' if healing else 'damage'})
        if not healing:
            if hasattr(self,'damage_summary'):self.summary.setText(self.damage_summary)
            return
        fight=self.report['fights'][-1];actor=next((a for a in fight.get('actors',[]) if a['id']==self.actor_id),{})
        valid=fight.get('integrity','ok')=='ok';seconds=max(1,fight.get('healing_seconds',fight.get('seconds',1)))
        from .healing import observed_amount
        amount=observed_amount(fight,actor);hps=amount/seconds if amount is not None and valid else None
        self.summary.setText(_tr('{0} HPS · {1} Heilung · Selbst {2} · Andere {3}\n' ,number(hps),number(amount) if valid else '—',number(actor.get('self_healing')) if valid else '—',number(actor.get('other_healing')) if valid else '—')+equipment_text(actor))

class FightHistory(QDialog):
    def __init__(self,current,directory,parent=None):
        super().__init__(parent);self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose);self.setWindowTitle(_tr('Kampfverlauf'));self.resize(560,650);self.reports=[];self.dialogs=[];self.skill_labels=getattr(parent,'skill_labels',SKILL_LABELS)
        layout=QVBoxLayout(self);self.choice=QComboBox();layout.addWidget(self.choice)
        current=deepcopy(current)
        for fight in reversed(current.get('fights',[])):
            self.add({**current,'fights':[fight]},_tr('Diese Sitzung'))
        seen={(current.get('session',{}).get('id'),f['id']) for f in current.get('fights',[])}
        skipped=0
        for path in sorted(Path(directory).glob('combat_*.json'),reverse=True)[:100]:
            try:
                doc=json.loads(path.read_text(encoding='utf-8'));fight=doc['fight'];session=doc.get('session',{});key=(session.get('id'),fight['id'])
                if key in seen:continue
                if not isinstance(fight.get('actors'),list) or not isinstance(fight.get('skills'),list) or not isinstance(fight.get('seconds'),(int,float)):raise ValueError('invalid fight')
                report={'fights':[fight],'self_identity':doc.get('self_identity',{}),'self_id':doc.get('self_identity',{}).get('id'),'session':session};self.add(report,_tr('Gespeichert'));seen.add(key)
            except (OSError,ValueError,KeyError,TypeError):skipped+=1
        self.status=QLabel();self.status.setWordWrap(True);layout.addWidget(self.status);self.view=DamageView();layout.addWidget(self.view,2);self.graph=DamageView(True);layout.addWidget(self.graph,1)
        note=QLabel(_tr('Gespeicherte Kämpfe werden getrennt vom Live-Meter angezeigt. Spieler anklicken für Details.'));note.setWordWrap(True);layout.addWidget(note)
        buttons=QHBoxLayout();self.copy_fight=QPushButton(_tr('Boss/Kampf kopieren'));self.copy_dungeon=QPushButton(_tr('Dungeon kopieren'));buttons.addWidget(self.copy_fight);buttons.addWidget(self.copy_dungeon);layout.addLayout(buttons)
        self.copy_status=QLabel();self.copy_status.setWordWrap(True);layout.addWidget(self.copy_status)
        self.copy_fight.clicked.connect(self.copy_selected_fight);self.copy_dungeon.clicked.connect(self.copy_selected_dungeon)
        self.directory=Path(directory);self.export_current=deepcopy(current);self.export_controller=ExportController(self)
        self.save_log=QPushButton(_tr('Dungeon-Log speichern'));buttons.addWidget(self.save_log)
        self.save_log.clicked.connect(self.export_dungeon_log)
        self.all_reports=list(self.reports);self.raw_reports=deepcopy(self.reports);self.history_items=[self.choice.itemText(i) for i in range(self.choice.count())]
        from .encounter_history import EncounterAnnotations,OUTCOMES
        self.annotations=EncounterAnnotations(self.directory);self.run_choice=QComboBox();layout.insertWidget(0,self.run_choice);self.run_choice.currentIndexChanged.connect(lambda:self.filter_bosses(self.boss_filter.isChecked()))
        from .metrics import METRICS
        self.history_metric=QComboBox()
        for key,label in METRICS.items():self.history_metric.addItem(label,key)
        layout.insertWidget(1,self.history_metric);self.history_metric.currentIndexChanged.connect(lambda:self.select(self.choice.currentIndex()))
        marks=QHBoxLayout();self.outcome_choice=QComboBox()
        for key,label in OUTCOMES.items():self.outcome_choice.addItem(label,key)
        self.outcome_choice.activated.connect(self.mark_outcome);marks.addWidget(self.outcome_choice);self.split_run=QPushButton(_tr('Durchlauf ab hier'));self.split_run.clicked.connect(self.mark_run);self.split_run.setToolTip(_tr('Markiert eine manuelle Grenze ab diesem Kampf. Originaldateien bleiben erhalten. Erneut klicken hebt diese Grenze auf.'));marks.addWidget(self.split_run);layout.addLayout(marks)
        self.compare_button=QPushButton(_tr('Kämpfe vergleichen'));self.compare_button.clicked.connect(self.compare);buttons.addWidget(self.compare_button)
        self.boss_filter=QCheckBox(_tr('Nur Bosskämpfe'));self.boss_filter.setToolTip(_tr('Bosskämpfe einzeln auswählen, auch nach Ende des Runs'));layout.insertWidget(0,self.boss_filter);self.boss_filter.toggled.connect(self.filter_bosses)
        self.boss_filter.hide()
        from .encounter_scope import scope_label
        self.scope_choice=QComboBox()
        for key in ('all','boss','trash','unknown'):self.scope_choice.addItem(scope_label(key),key)
        self.scope_choice.currentIndexChanged.connect(self.change_scope);layout.insertWidget(0,self.scope_choice)
        self.choice.currentIndexChanged.connect(self.select);self.view.actorClicked.connect(self.details);self.select(self.choice.currentIndex())
        self.refresh_annotations()
        if skipped:self.status.setText(self.status.text()+_tr(' · {0} Dateien nicht lesbar' ,skipped))
    def filter_bosses(self,enabled):
        from .encounter_scope import project_report,encounter_kind,scope_label
        scope='boss' if enabled else (self.scope_choice.currentData() if hasattr(self,'scope_choice') else 'all')
        index=self.choice.currentIndex()
        previous=self.reports[index] if 0<=index<len(self.reports) else None
        self.choice.blockSignals(True);self.choice.clear();self.reports=[]
        for report,caption in zip(self.all_reports,self.history_items):
            fight=report['fights'][-1]
            from .chat_export import run_identity
            selected_run=self.run_choice.currentData() if hasattr(self,'run_choice') else ''
            if selected_run and json.dumps(run_identity(report))!=selected_run:continue
            scoped=project_report(report,scope)
            if scoped is None:continue
            if scope!='all':
                sf=scoped['fights'][-1]
                caption=scope_label(scope)+' · '+str(sf.get('boss_name') or sf.get('target_name') or _tr('Kampf'))+' · '+str(int(sf.get('seconds',0)))+' s'
            else:caption='['+scope_label(encounter_kind(fight))+'] '+caption
            self.reports.append(scoped);self.choice.addItem(caption)
        if previous in self.reports:self.choice.setCurrentIndex(self.reports.index(previous))
        self.choice.blockSignals(False);self.select(self.choice.currentIndex())
    def change_scope(self,*args):
        self.boss_filter.blockSignals(True);self.boss_filter.setChecked(False);self.boss_filter.blockSignals(False);self.filter_bosses(False)
    def refresh_annotations(self):
        from .encounter_history import fight_key
        index=self.choice.currentIndex();chosen=fight_key(self.reports[index],self.reports[index]['fights'][-1]) if 0<=index<len(self.reports) else None
        from .chat_export import run_identity
        from .encounter_history import outcome
        try:self.all_reports=[self.annotations.apply(r) for r in self.raw_reports]
        except (OSError,ValueError) as error:self.copy_status.setText(_tr('Markierungen nicht lesbar: ')+str(error));self.all_reports=deepcopy(self.raw_reports)
        self.history_items=[];groups={};attempts={}
        ordered=sorted(self.all_reports,key=lambda r:r['fights'][-1].get('start_ms',0))
        indices={}
        for r in ordered:
            f=r['fights'][-1];key=(json.dumps(run_identity(r)),f.get('boss_template') or f.get('boss_name'))
            attempts[key]=attempts.get(key,0)+1;indices[(r.get('session',{}).get('id'),str(f['id']))]=attempts[key]
        from datetime import datetime
        for r in self.all_reports:
            f=r['fights'][-1];stamp=datetime.fromtimestamp(f.get('start_ms',0)/1000).strftime('%d.%m. %H:%M:%S');run=run_identity(r)
            section=indices[r.get('session',{}).get('id'),str(f['id'])]
            area=f.get('dungeon_name') or f.get('region_name')
            self.history_items.append(f"{stamp} · "+(area+' · ' if area else '')+_tr('{0} · Abschnitt {1} · {2}' ,f.get('boss_name') or f.get('target_name') or 'Kampf',section,outcome(f)))
            if run is not None:groups.setdefault(json.dumps(run),(stamp,f.get('dungeon_name','Dungeon')))
        self.run_choice.blockSignals(True);self.run_choice.clear();self.run_choice.addItem(_tr('Alle Durchläufe'),'')
        for key,(stamp,name) in groups.items():self.run_choice.addItem(_tr('{0} · {1} · lokale Zuordnung' ,name,stamp),key)
        self.run_choice.blockSignals(False);self.filter_bosses(self.boss_filter.isChecked())
        for i,r in enumerate(self.reports):
            if fight_key(r,r['fights'][-1])==chosen:self.choice.setCurrentIndex(i);break
    def mark_outcome(self,index):
        selected=self.choice.currentIndex()
        if not 0<=selected<len(self.reports):return
        try:self.annotations.write(self.reports[selected],outcome=self.outcome_choice.currentData());self.refresh_annotations()
        except (OSError,ValueError) as error:self.copy_status.setText(_tr('Markierung nicht gespeichert: ')+str(error))
    def mark_run(self):
        selected=self.choice.currentIndex()
        if not 0<=selected<len(self.reports):return
        r=self.reports[selected]
        if not r['fights'][-1].get('run_key'):self.copy_status.setText(_tr('Keine lokale Dungeon-Zuordnung vorhanden.'));return
        try:self.annotations.write(r,run_start=not r['fights'][-1].get('manual_run_start',False));self.refresh_annotations()
        except (OSError,ValueError) as error:self.copy_status.setText(_tr('Durchlaufgrenze nicht gespeichert: ')+str(error))
    def compare(self):
        index=self.choice.currentIndex()
        if not 0<=index<len(self.reports):return
        from .comparison import FightComparison
        from .encounter_scope import project_report
        scope=self.reports[index]['fights'][-1].get('damage_scope','all')
        reports=[r for report in self.all_reports if (r:=project_report(report,scope)) is not None]
        dialog=FightComparison(self.reports[index],reports,self);self.dialogs.append(dialog);dialog.destroyed.connect(lambda:self.forget(dialog));dialog.show()
    def add(self,report,source):
        from .personal_boss import personal_report
        report=personal_report(report)
        from datetime import datetime
        f=report['fights'][-1];stamp=datetime.fromtimestamp(f.get('start_ms',0)/1000).strftime('%d.%m. %H:%M:%S')
        self.reports.append(deepcopy(report));self.choice.addItem(f"{stamp} · {(f.get('dungeon_name') or f.get('region_name'))+' · ' if (f.get('dungeon_name') or f.get('region_name')) else ''}{f.get('boss_name') or f.get('target_name') or _tr('Kampf')} · {int(f.get('seconds',0))} s · {source}")
    def select(self,index):
        from .chat_export import dungeon_reports
        available=0<=index<len(self.reports)
        self.copy_fight.setEnabled(available)
        if hasattr(self,'compare_button'):
            from .comparison import comparable
            self.compare_button.setEnabled(available and any(comparable(self.reports[index],r) for r in self.all_reports if r is not self.reports[index]))
            self.split_run.setEnabled(available and bool(self.reports[index]['fights'][-1].get('run_key')))
            self.outcome_choice.setEnabled(available)
            if available:self.outcome_choice.setCurrentIndex(max(0,self.outcome_choice.findData(self.reports[index]['fights'][-1].get('manual_outcome',''))))
        grouped=dungeon_reports(self.all_reports,self.reports[index]) if available else []
        self.copy_dungeon.setEnabled(bool(grouped))
        from .chat_export import run_identity
        exportable=available and run_identity(self.reports[index]) is not None
        self.save_log.setEnabled(exportable)
        self.copy_dungeon.setToolTip(_tr('Beobachtete Bosskämpfe dieser Dungeon-Instanz kopieren') if grouped else _tr('Dungeon-Instanz noch nicht eindeutig erkannt; einzelnen Kampf kopieren.'))
        self.copy_status.clear()
        if not available:
            self.status.setText(_tr('Keine erkannten Bosskämpfe vorhanden.') if self.boss_filter.isChecked() else _tr('Noch keine gespeicherten Kämpfe.'))
            self.view.set_data({'fights':[]},{});self.graph.set_data({'fights':[]},{})
            return
        r=self.reports[index]
        from .metrics import metric_report,METRICS
        mode=self.history_metric.currentData();f=metric_report(r,mode)['fights'][-1];rate='DPS' if mode=='damage' else 'HPS'
        self.status.setText(f"{number(f.get('dps'))} {rate} · {number(f.get('total_damage'))} {METRICS[mode]}"+(_tr(' · Teilausschnitt') if f.get('partial') else ''));settings={'display_metric':mode};self.view.set_data(r,settings);self.graph.set_data(r,settings)
        if f.get('scope_note'):self.status.setText(self.status.text()+'\n'+f['scope_note'])
    def copy_selected_fight(self):
        from .chat_export import fight_text
        index=self.choice.currentIndex()
        if 0<=index<len(self.reports):
            from .chat_export import healing_text
            mode=self.history_metric.currentData();self.copy_text(fight_text(self.reports[index]) if mode=='damage' else healing_text(self.reports[index],mode))
    def copy_selected_dungeon(self):
        from .chat_export import dungeon_text
        index=self.choice.currentIndex()
        if 0<=index<len(self.reports):self.copy_text(dungeon_text(self.all_reports,self.reports[index]))
    def export_dungeon_log(self):
        index=self.choice.currentIndex()
        if not 0<=index<len(self.reports):return
        destination,_=QFileDialog.getSaveFileName(self,_tr('Dungeon-Log speichern'),'dungeon-log.json','JSON (*.json)')
        if not destination:return
        self.export_controller.start(self.directory,self.export_current,self.reports[index],destination,self.copy_status,self.save_log)

    def copy_text(self,text):
        from PySide6.QtWidgets import QApplication
        if text:
            QApplication.clipboard().setText(text)
            self.copy_status.setText(_tr('Chattext kopiert – im Spiel einfügen.'))
    def details(self,actor):
        index=self.choice.currentIndex()
        if not 0<=index<len(self.reports):return
        dialog=PlayerDetails(self.reports[index],actor,self);self.dialogs.append(dialog);dialog.destroyed.connect(lambda:self.forget(dialog));dialog.show()
    def forget(self,dialog):
        if dialog in self.dialogs:self.dialogs.remove(dialog)
