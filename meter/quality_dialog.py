from .language import tr as _tr
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog,QVBoxLayout,QLabel,QTableWidget,QTableWidgetItem,QHeaderView
from .quality import player_quality

class QualityDialog(QDialog):
    def __init__(self,report,parent=None):
        super().__init__(parent);self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose);self.setWindowTitle(_tr('Datenqualität pro Spieler'));self.resize(960,440)
        self.session=report.get('session',{}).get('id');self.fight_id=report.get('fights',[{}])[-1].get('id') if report.get('fights') else None
        layout=QVBoxLayout(self);note=QLabel(_tr('Belege der Erfassung, keine Vollständigkeitsbewertung. Fehlende Mengen sind kein Beweis für Netzwerkverlust. Worldboss/Open World bleiben offen.'));note.setWordWrap(True);layout.addWidget(note)
        self.table=QTableWidget();self.table.setColumnCount(6);self.table.setHorizontalHeaderLabels([_tr('Spieler'),_tr('Status'),_tr('Damage-Ereignisse'),_tr('Heil-Ereignisse'),_tr('Casts / Trigger'),_tr('Hinweise')]);self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers);self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents);self.table.horizontalHeader().setSectionResizeMode(5,QHeaderView.ResizeMode.Stretch);layout.addWidget(self.table);self.set_report(report)
    def set_report(self,report):
        if report.get('session',{}).get('id')!=self.session:return
        fights=report.get('fights',[])
        if self.fight_id is None and fights:self.fight_id=fights[-1]['id']
        fight=next((f for f in fights if f['id']==self.fight_id),None)
        if fight is None:return
        actors=fight.get('actors',[]);self.table.setRowCount(len(actors))
        for i,actor in enumerate(actors):
            q=player_quality(actor,fight);values=[actor.get('name') or f"Entity {actor['id']}",q['label'],q['damage_events'] if q['damage_events'] is not None else '—',q['healing_events'] if q['healing_events'] is not None else '—',q['casts'] if q['casts'] is not None else '—','; '.join(q['notes']) or _tr('Nur beobachtete Werte; Vollständigkeit nicht bestätigt')]
            for j,value in enumerate(values):
                item=QTableWidgetItem(str(value));item.setToolTip(str(value));self.table.setItem(i,j,item)
