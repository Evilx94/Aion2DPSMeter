"""Background log catalogue, filters, paging and reviewed reversible archiving."""
from .language import tr as _tr,decimal
from pathlib import Path
from datetime import datetime,timedelta
from threading import Event
from PySide6.QtCore import Qt,QThreadPool,QDate
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QFormLayout,QLineEdit,QCheckBox,QDateEdit,QPushButton,QLabel,QTableWidget,QTableWidgetItem,QHeaderView,QSpinBox,QDialogButtonBox
from .background import Task
from .log_management import scan_logs,filter_records,storage_size,archive_candidates,archive_files,restore_file,report_from_file

def size_text(n):return decimal(f'{n/1024/1024:.1f} MiB')

class ArchivePreview(QDialog):
    def __init__(self,plan,parent=None):
        super().__init__(parent);self.setWindowTitle(_tr('Archivierung prüfen'));self.resize(840,450)
        layout=QVBoxLayout(self);note=QLabel(_tr('{0} Dateien · {1}\nVerschiebt in .archive unter dem jeweiligen Ordner. Kein Löschen und keine Inhaltsänderung. Auf demselben Laufwerk wird dadurch kein Speicher frei.' ,len(plan),size_text(sum((p['size'] for p in plan)))));note.setWordWrap(True);layout.addWidget(note)
        table=QTableWidget(len(plan),3);table.setHorizontalHeaderLabels([_tr('Datei'),_tr('Art'),_tr('Größe')]);table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers);table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch)
        for i,item in enumerate(plan):
            for j,value in enumerate((item['path'],item['kind'],size_text(item['size']))):table.setItem(i,j,QTableWidgetItem(value))
        layout.addWidget(table);buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel);buttons.button(QDialogButtonBox.StandardButton.Ok).setText(_tr('Ins Archiv verschieben'));buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject);layout.addWidget(buttons)

class LogBrowser(QDialog):
    PAGE_SIZE=100
    def __init__(self,directory,data_directory,current=None,preferences=None,parent=None):
        super().__init__(parent);self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose);self.setWindowTitle(_tr('Log-Verwaltung'));self.resize(1000,700)
        from .preferences import Preferences
        self.directory=Path(directory);self.data_directory=Path(data_directory);self.current=current or {};self.preferences=preferences or Preferences(data_directory)
        self.records=[];self.filtered=[];self.page=0;self.jobs=[];self.serial=0;self.dialogs=[];self.anchor=None;self.cancel_scan=Event()
        layout=QVBoxLayout(self);form=QFormLayout();self.boss=QLineEdit();self.character=QLineEdit();self.area=QLineEdit()
        form.addRow(_tr('Boss / Gegner'),self.boss);form.addRow(_tr('Charakter / Beteiligter'),self.character);form.addRow('Dungeon / Region',self.area);layout.addLayout(form)
        dates=QHBoxLayout();self.date_enabled=QCheckBox(_tr('Datum eingrenzen'));dates.addWidget(self.date_enabled)
        self.from_date=QDateEdit(QDate.currentDate().addDays(-30));self.to_date=QDateEdit(QDate.currentDate())
        for widget in (self.from_date,self.to_date):widget.setCalendarPopup(True);dates.addWidget(widget);widget.dateChanged.connect(self.apply_filters)
        self.archive_toggle=QCheckBox(_tr('Archiv einbeziehen'));dates.addWidget(self.archive_toggle);self.archive_toggle.toggled.connect(self.refresh)
        refresh=QPushButton(_tr('Aktualisieren'));refresh.clicked.connect(self.refresh);dates.addWidget(refresh);layout.addLayout(dates)
        for widget in (self.boss,self.character,self.area):widget.textChanged.connect(self.apply_filters)
        self.date_enabled.toggled.connect(self.apply_filters)
        self.summary=QLabel();self.summary.setWordWrap(True);layout.addWidget(self.summary)
        self.table=QTableWidget();self.table.setColumnCount(6);self.table.setHorizontalHeaderLabels([_tr('Zeit'),_tr('Charakter'),_tr('Ort'),_tr('Boss / Gegner'),_tr('Ende'),_tr('Größe')]);self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers);self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows);self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection);self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents);self.table.horizontalHeader().setSectionResizeMode(3,QHeaderView.ResizeMode.Stretch);layout.addWidget(self.table,1)
        nav=QHBoxLayout();self.previous=QPushButton(_tr('Zurück'));self.next=QPushButton(_tr('Weiter'));self.page_label=QLabel();nav.addWidget(self.previous);nav.addWidget(self.page_label);nav.addWidget(self.next);layout.addLayout(nav);self.previous.clicked.connect(lambda:self.change_page(-1));self.next.clicked.connect(lambda:self.change_page(1))
        actions=QHBoxLayout();open_button=QPushButton(_tr('Kampf öffnen'));open_button.clicked.connect(self.open_selected);actions.addWidget(open_button);anchor=QPushButton(_tr('Als Vergleich A'));anchor.clicked.connect(self.set_anchor);actions.addWidget(anchor);compare=QPushButton(_tr('Mit A vergleichen'));compare.clicked.connect(self.compare_selected);actions.addWidget(compare);restore=QPushButton(_tr('Aus Archiv wiederherstellen'));restore.clicked.connect(self.restore_selected);actions.addWidget(restore);layout.addLayout(actions)
        self.anchor_label=QLabel(_tr('Vergleich A: noch nicht gewählt'));layout.addWidget(self.anchor_label)
        retention=QHBoxLayout();retention.addWidget(QLabel(_tr('Archivvorschlag nach Tagen · 0 = aus')))
        self.combat_days=QSpinBox();self.capture_days=QSpinBox()
        for widget,key,label in ((self.combat_days,'archive_combat_days',_tr('Kampflogs')),(self.capture_days,'archive_capture_days',_tr('Mitschnitte'))):
            widget.setRange(0,3650);widget.setValue(self.preferences.values.get(key,0));retention.addWidget(QLabel(label));retention.addWidget(widget)
        save=QPushButton(_tr('Speichern'));save.clicked.connect(self.save_retention);retention.addWidget(save);self.archive_button=QPushButton(_tr('Archivierung prüfen'));self.archive_button.clicked.connect(self.preview_archive);retention.addWidget(self.archive_button);layout.addLayout(retention)
        self.message=QLabel(_tr('Worldboss/Open World: weiterhin offene Erfassung, keine bestätigte Vollständigkeit.'));self.message.setWordWrap(True);layout.addWidget(self.message)
        self.table.cellDoubleClicked.connect(lambda *args:self.open_selected());self.refresh()
    def start(self,kind,function,*args,**kwargs):
        task=Task(function,*args,**kwargs);task.kind=kind;task.serial=self.serial;self.jobs.append(task)
        task.signals.ready.connect(self.ready,Qt.ConnectionType.QueuedConnection);task.signals.failed.connect(self.failed,Qt.ConnectionType.QueuedConnection);QThreadPool.globalInstance().start(task)
    def refresh(self,*args):
        self.cancel_scan.set();self.cancel_scan=Event();self.serial+=1;self.summary.setText(_tr('Logbestand wird im Hintergrund gelesen …'));self.start('scan',self.scan,self.directory,self.data_directory,self.archive_toggle.isChecked(),self.cancel_scan)
    @staticmethod
    def scan(directory,data_directory,include_archive,cancel):
        return scan_logs(directory,include_archive,cancel),storage_size(data_directory/'captures','live_*.pcap')
    def closeEvent(self,event):
        self.cancel_scan.set();super().closeEvent(event)
    def ready(self,result):
        task=next((t for t in self.jobs if t.signals==self.sender()),None)
        if task is None:return
        self.jobs.remove(task)
        if task.kind=='scan':
            if task.serial!=self.serial:return
            scan,storage=result;self.records=scan['records'];self.summary.setText(_tr('{0} Kämpfe · {1} Logdateien · {2} · {3} Lesefehler\nAktive Mitschnitte: {4} Dateien · {5}' ,len(self.records),scan['physical_files'],size_text(scan['bytes']),len(scan['errors']),storage[0],size_text(storage[1])));self.apply_filters()
        elif task.kind=='plan':
            self.archive_button.setEnabled(True)
            if not result:self.message.setText(_tr('Keine geeigneten alten, geschlossenen Dateien. Aktuelle Sitzung/Mitschnitte sind geschützt.'));return
            preview=ArchivePreview(result,self)
            if preview.exec()==QDialog.DialogCode.Accepted:self.start('archive',archive_files,result)
            preview.deleteLater()
        elif task.kind=='archive':self.message.setText(_tr('{0} Dateien archiviert · {1} übersprungen/fehlgeschlagen' ,len(result['moved']),len(result['errors'])));self.refresh()
    def failed(self,error):
        task=next((t for t in self.jobs if t.signals==self.sender()),None)
        if task:self.jobs.remove(task)
        self.archive_button.setEnabled(True);self.message.setText(_tr('Vorgang fehlgeschlagen: ')+error)
    def apply_filters(self,*args):
        start=end=None
        if self.date_enabled.isChecked():
            first=self.from_date.date();last=self.to_date.date()
            start=int(datetime(first.year(),first.month(),first.day()).timestamp()*1000);end=int((datetime(last.year(),last.month(),last.day())+timedelta(days=1)).timestamp()*1000)
        self.filtered=filter_records(self.records,self.boss.text(),self.character.text(),self.area.text(),start,end);self.page=0;self.render_page()
    def change_page(self,delta):self.page=max(0,min(max(0,(len(self.filtered)-1)//self.PAGE_SIZE),self.page+delta));self.render_page()
    def render_page(self):
        rows=self.filtered[self.page*self.PAGE_SIZE:(self.page+1)*self.PAGE_SIZE];self.table.setRowCount(len(rows))
        for i,r in enumerate(rows):
            values=[datetime.fromtimestamp(r['start_ms']/1000).strftime('%d.%m.%Y %H:%M:%S'),r['character'] or ', '.join(r['people']),r['area'],r['boss'],r.get('outcome',_tr('Ende unbestätigt')),size_text(r['size'])]
            for j,value in enumerate(values):self.table.setItem(i,j,QTableWidgetItem(str(value)))
            self.table.item(i,0).setToolTip(r['path'])
        pages=max(1,(len(self.filtered)+self.PAGE_SIZE-1)//self.PAGE_SIZE);self.page_label.setText(_tr('Seite {0}/{1} · {2} Treffer' ,self.page + 1,pages,len(self.filtered)));self.previous.setEnabled(self.page>0);self.next.setEnabled(self.page+1<pages)
    def selected(self):
        row=self.table.currentRow();index=self.page*self.PAGE_SIZE+row
        return self.filtered[index] if row>=0 and index<len(self.filtered) else None
    def selected_report(self):
        item=self.selected()
        if item is None:return None
        return report_from_file(item['path'],self.directory)
    def show_dialog(self,dialog):self.dialogs.append(dialog);dialog.show()
    def open_selected(self):
        from .details import FightHistory
        try:
            report=self.selected_report()
            if report:self.show_dialog(FightHistory(report,self.directory,self))
        except (OSError,ValueError,KeyError) as error:self.message.setText(str(error))
    def set_anchor(self):
        try:
            self.anchor=self.selected_report()
            if self.anchor:self.anchor_label.setText(_tr('Vergleich A: ')+str(self.anchor['fights'][-1].get('boss_name') or _tr('Kampf')))
        except (OSError,ValueError,KeyError) as error:self.message.setText(str(error))
    def compare_selected(self):
        from .comparison import comparable,FightComparison
        try:
            report=self.selected_report()
            if self.anchor and report and comparable(self.anchor,report):self.show_dialog(FightComparison(self.anchor,[report],self))
            else:self.message.setText(_tr('Zwei unterschiedliche Kämpfe mit bestätigtem gleichem Boss-Template und gleicher Karte wählen.'))
        except (OSError,ValueError,KeyError) as error:self.message.setText(str(error))
    def save_retention(self):
        self.preferences.values.update(archive_combat_days=self.combat_days.value(),archive_capture_days=self.capture_days.value());self.preferences.save();self.message.setText(_tr('Aufbewahrungsgrenzen für Archivvorschläge gespeichert; keine automatische Löschung.'))
    def preview_archive(self):
        self.save_retention();self.archive_button.setEnabled(False);session=self.current.get('session',{});paths=[session.get('recording'),*session.get('recordings',[])]
        self.start('plan',archive_candidates,self.directory,self.data_directory/'captures',self.combat_days.value(),self.capture_days.value(),[session.get('id')],paths)
    def restore_selected(self):
        item=self.selected()
        if not item or not item['archived']:self.message.setText(_tr('Einen Eintrag aus dem eingeblendeten Archiv wählen.'));return
        try:restore_file(item['path'],self.directory);self.message.setText(_tr('Datei wiederhergestellt.'));self.refresh()
        except (OSError,ValueError) as error:self.message.setText(str(error))
