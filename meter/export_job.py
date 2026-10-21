"""Background export preparation keeps capture/rendering responsive."""
from .language import tr as _tr
from copy import deepcopy
from PySide6.QtCore import QObject,Signal,QRunnable,QThreadPool,Qt
from PySide6.QtWidgets import QApplication,QFileDialog

class ExportSignals(QObject):
    ready=Signal(object,str)
    failed=Signal(str)

class DungeonExportJob(QRunnable):
    def __init__(self,directory,current,selected,destination):
        super().__init__();self.directory=directory;self.current=deepcopy(current);self.selected=deepcopy(selected);self.destination=destination;self.signals=ExportSignals()
    def run(self):
        try:
            from .dungeon_export import load_dungeon_log
            self.signals.ready.emit(load_dungeon_log(self.directory,self.current,self.selected),self.destination)
        except Exception as error:self.signals.failed.emit(str(error))

class ExportController(QObject):
    def __init__(self,parent):super().__init__(parent);self.jobs=[]
    def start(self,directory,current,selected,destination='',status=None,button=None,output='json'):
        if button:button.setEnabled(False)
        if status:status.setText(_tr('Dungeon-Chattext wird zusammengestellt …') if output=='chat' else _tr('Dungeon-Log wird aus allen gespeicherten Kämpfen zusammengestellt …'))
        job=DungeonExportJob(directory,current,selected,destination);self.jobs.append(job)
        # Explicit queued delivery; no clipboard/UI access from the worker thread.
        job.signals.ready.connect(self.ready,Qt.ConnectionType.QueuedConnection)
        job.signals.failed.connect(self.failed,Qt.ConnectionType.QueuedConnection)
        job.status=status;job.button=button;job.output=output;QThreadPool.globalInstance().start(job)
    def finish(self,job):
        if job.button:job.button.setEnabled(True)
        self.jobs.remove(job)
    def ready(self,document,destination):
        job=next((j for j in self.jobs if j.signals==self.sender()),None)
        if job is None:return
        try:
            from .dungeon_export import serialized_log,save_log
            if job.output=='chat':
                from .chat_export import dungeon_text
                reports=[{'session':document['session'],'fights':[fight]} for fight in document['fights']]
                text=dungeon_text(reports,reports[-1])
                if not text:raise ValueError(_tr('Noch keine erfassten Bosskämpfe zum Kopieren.'))
                QApplication.clipboard().setText(text);message=_tr('Dungeon-Chattext kopiert – im Spiel einfügen.')
            elif destination:
                path=save_log(document,destination);message=_tr('Dungeon-Log gespeichert: ')+str(path)
            else:QApplication.clipboard().setText(serialized_log(document));message=_tr('Vollständiger gespeicherter Dungeon-Log als JSON kopiert.')
            if job.status:job.status.setText(message)
        except (OSError,ValueError) as error:
            if job.status:job.status.setText(_tr('Export fehlgeschlagen: ')+str(error))
        finally:self.finish(job)
    def failed(self,error):
        job=next((j for j in self.jobs if j.signals==self.sender()),None)
        if job:
            if job.status:job.status.setText(_tr('Export fehlgeschlagen: ')+error)
            self.finish(job)
