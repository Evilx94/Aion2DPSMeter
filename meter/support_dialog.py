"""Explicit content choices and local save, with ZIP creation off the UI thread."""
from .language import tr as _tr
from copy import deepcopy
from pathlib import Path
from PySide6.QtCore import Qt,QThreadPool
from PySide6.QtWidgets import QDialog,QVBoxLayout,QLabel,QCheckBox,QPushButton,QFileDialog
from .background import Task
from .support_export import build_bundle,save_bundle

def export(report,settings,sections,log_directory,path):return str(save_bundle(build_bundle(report,settings,sections,log_directory),path))

class SupportDialog(QDialog):
    def __init__(self,report,settings,data_directory,parent=None):
        super().__init__(parent);self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose);self.setWindowTitle(_tr('Diagnoseexport'));self.resize(560,330)
        self.report=deepcopy(report);self.settings=deepcopy(settings);self.data_directory=Path(data_directory);self.jobs=[]
        layout=QVBoxLayout(self);note=QLabel(_tr('Speichert eine lokale ZIP-Datei. Kein Upload, keine PCAPs, keine vollständige Config und keine Adapterkennung. Worldboss/Open World bleiben offene Bereiche.'));note.setWordWrap(True);layout.addWidget(note)
        self.sections={}
        for key,text,checked in (('counters',_tr('Netzwerk-, Decoder- und Erfassungszähler'),True),('settings',_tr('Anzeige-/Speicheroptionen ohne Namen und Pfade'),True),('fight',_tr('Aktueller Kampf mit ersetzten Spielernamen (Zeiten/Spielwerte bleiben)'),False),('errors',_tr('Bis zu drei gekürzte Fehlerprotokolle (können weitere persönliche Angaben enthalten)'),False)):
            box=QCheckBox(text);box.setChecked(checked);layout.addWidget(box);self.sections[key]=box
        self.message=QLabel(_tr('Inhalte vor dem Teilen prüfen. Bekannte Namen, IPs und Pfade werden in Fehlertexten bestmöglich ersetzt.'));self.message.setWordWrap(True);layout.addWidget(self.message)
        self.save=QPushButton(_tr('Diagnose-ZIP speichern'));self.save.clicked.connect(self.choose_destination);layout.addWidget(self.save)
    def choose_destination(self):
        path,_=QFileDialog.getSaveFileName(self,_tr('Diagnose speichern'),'aion2-diagnose.zip','ZIP (*.zip)')
        if path:self.start_export(path)
    def start_export(self,path):
        self.save.setEnabled(False);self.message.setText(_tr('Diagnose wird im Hintergrund erstellt …'))
        sections=[key for key,box in self.sections.items() if box.isChecked()]
        task=Task(export,self.report,self.settings,sections,self.data_directory/'logs',path);self.jobs.append(task)
        task.signals.ready.connect(self.ready,Qt.ConnectionType.QueuedConnection);task.signals.failed.connect(self.failed,Qt.ConnectionType.QueuedConnection);QThreadPool.globalInstance().start(task)
    def ready(self,path):self.jobs.clear();self.save.setEnabled(True);self.message.setText(_tr('Lokal gespeichert: ')+path+_tr(' · Es wurde nichts versendet.'))
    def failed(self,error):self.jobs.clear();self.save.setEnabled(True);self.message.setText(_tr('Export fehlgeschlagen: ')+error)
