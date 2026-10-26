"""User-triggered updates; network and package validation stay off the UI thread."""
from pathlib import Path
from threading import Event
from PySide6.QtCore import Qt,QObject,Signal,QRunnable,QThreadPool,QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QCheckBox,QPlainTextEdit,QProgressBar
from .language import text
from . import __version__
from . import updates

GERMAN_ERRORS={
 'network':'GitHub ist derzeit nicht erreichbar. Bitte später erneut versuchen.',
 'cancelled':'Update abgebrochen.',
 'metadata':'Ungültige Release-Informationen.',
 'url':'Die Update-Adresse gehört nicht zum offiziellen Repository.',
 'checksum_missing':'Dieses Release hat keine SHA-256-Prüfsumme. Bitte die GitHub-Seite öffnen.',
 'checksum':'Die SHA-256-Prüfung des heruntergeladenen Pakets ist fehlgeschlagen.',
 'package':'Das Update-Paket oder sein Dateimanifest ist ungültig.',
 'size':'Das Update überschreitet die erlaubte Größe.',
 'asset':'An diesem Release hängt kein passendes Update-Paket.',
 'version':'Das Update ist nicht neuer als die installierte Version.',
 'storage':'Das Update konnte nicht gespeichert werden. Speicherplatz und Ordnerzugriff prüfen.',
}

class UpdateSignals(QObject):
    ready=Signal(object)
    failed=Signal(str)
    progress=Signal(int,int)

class UpdateTask(QRunnable):
    def __init__(self,kind,cancel,*args):
        super().__init__();self.kind=kind;self.cancel=cancel;self.args=args;self.signals=UpdateSignals()
    def run(self):
        try:
            if self.kind=='check':result=updates.check_updates(*self.args,cancel=self.cancel)
            else:result=updates.prepare_update(*self.args,cancel=self.cancel,progress=self.signals.progress.emit)
            self.signals.ready.emit(result)
        except updates.UpdateError as error:self.signals.failed.emit(error.code)
        except Exception:self.signals.failed.emit('network' if self.kind=='check' else 'storage')

class UpdateDialog(QDialog):
    def __init__(self,directory,settings,preferences=None,parent=None):
        super().__init__(parent);self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.directory=Path(directory);self.settings=settings;self.preferences=preferences;self.language=settings.get('language','en')
        self.job=None;self.cancel=None;self.close_pending=False;self.release=None;self.prepared=None
        t=self.t;self.setWindowTitle(t('Updates','Updates'));self.resize(680,550)
        layout=QVBoxLayout(self)
        self.version=QLabel(t('Installed version: ','Installierte Version: ')+__version__);layout.addWidget(self.version)
        note=QLabel(t('Checks GitHub only when you click Check. Downloads are verified and prepared in a separate folder; your running meter, settings and logs are not replaced.','GitHub wird erst nach Klick auf Prüfen abgefragt. Downloads werden geprüft und in einem eigenen Ordner vorbereitet; laufendes Meter, Einstellungen und Logs werden nicht ersetzt.'));note.setWordWrap(True);layout.addWidget(note)
        self.preview=QCheckBox(t('Include beta / pre-release versions','Beta-/Vorabversionen berücksichtigen'));self.preview.setChecked(settings.get('update_prereleases',True));self.preview.toggled.connect(self.save_channel);layout.addWidget(self.preview)
        buttons=QHBoxLayout();self.check_button=QPushButton(t('Check for updates','Nach Updates suchen'));self.check_button.clicked.connect(self.check);buttons.addWidget(self.check_button)
        self.release_button=QPushButton(t('Open GitHub releases','GitHub-Releases öffnen'));self.release_button.clicked.connect(self.open_release);buttons.addWidget(self.release_button);layout.addLayout(buttons)
        self.status=QLabel(t('No update check performed yet.','Noch keine Update-Prüfung durchgeführt.'));self.status.setWordWrap(True);self.status.setTextFormat(Qt.TextFormat.PlainText);layout.addWidget(self.status)
        self.notes=QPlainTextEdit();self.notes.setReadOnly(True);self.notes.setPlaceholderText(t('Release notes appear here.','Hier erscheinen die Änderungshinweise.'));layout.addWidget(self.notes,1)
        self.progress=QProgressBar();self.progress.setRange(0,100);self.progress.setValue(0);self.progress.hide();layout.addWidget(self.progress)
        actions=QHBoxLayout();self.download_button=QPushButton(t('Download and verify','Herunterladen und prüfen'));self.download_button.setEnabled(False);self.download_button.clicked.connect(self.download);actions.addWidget(self.download_button)
        self.folder_button=QPushButton(t('Open prepared update','Vorbereitetes Update öffnen'));self.folder_button.setEnabled(False);self.folder_button.clicked.connect(self.open_folder);actions.addWidget(self.folder_button)
        self.cancel_button=QPushButton(t('Cancel download/check','Download/Prüfung abbrechen'));self.cancel_button.setEnabled(False);self.cancel_button.clicked.connect(self.cancel_work);actions.addWidget(self.cancel_button);layout.addLayout(actions)
        self.setStyleSheet('QDialog,QLabel,QCheckBox{background:#17242e;color:#dce9f2;} QPlainTextEdit{background:#243b49;color:#dce9f2;} QPushButton{padding:7px;}')
    def t(self,en,de):return text(self.language,en,de)
    def save_channel(self,checked):
        self.settings['update_prereleases']=checked
        if self.preferences:self.preferences.save()
        self.release=None;self.download_button.setEnabled(False)
        self.notes.clear();self.status.setText(self.t('Click Check to refresh this channel.','Zum Aktualisieren dieses Kanals auf Prüfen klicken.'))
    def start(self,kind,*args):
        if self.job:return
        self.cancel=Event();self.job=UpdateTask(kind,self.cancel,*args)
        self.job.signals.ready.connect(self.ready,Qt.ConnectionType.QueuedConnection)
        self.job.signals.failed.connect(self.failed,Qt.ConnectionType.QueuedConnection)
        self.job.signals.progress.connect(self.on_progress,Qt.ConnectionType.QueuedConnection)
        self.check_button.setEnabled(False);self.download_button.setEnabled(False);self.preview.setEnabled(False);self.cancel_button.setEnabled(True)
        self.progress.setRange(0,0);self.progress.show();QThreadPool.globalInstance().start(self.job)
    def check(self):
        if self.job:return
        self.release=None;self.notes.clear();self.status.setText(self.t('Checking GitHub …','GitHub wird geprüft …'))
        self.start('check',__version__,self.preview.isChecked())
    def checked(self,result):
        self.download_button.setEnabled(False)
        self.release=result['latest'];self.notes.setPlainText(self.release.notes if self.release else '')
        if not self.release:self.status.setText(self.t('No matching published release found.','Kein passendes veröffentlichtes Release gefunden.'));return
        version=self.release.version
        if result['available']:
            self.status.setText(self.t('New version available: ','Neue Version verfügbar: ')+version)
            if not self.release.package_url:self.status.setText(self.status.text()+'\n'+self.error_message('asset'))
            elif not self.release.verifiable:self.status.setText(self.status.text()+'\n'+self.error_message('checksum_missing'))
            self.download_button.setEnabled(self.release.verifiable)
        elif updates.version_key(version)<updates.version_key(__version__):self.status.setText(self.t('Your local version is newer than the latest matching published release: ','Deine lokale Version ist neuer als das letzte passende veröffentlichte Release: ')+version)
        else:self.status.setText(self.t('You are using the latest matching published version: ','Du nutzt die aktuelle passende veröffentlichte Version: ')+version)
    def download(self):
        if self.job or not self.release or not self.release.verifiable:return
        self.prepared=None;self.folder_button.setEnabled(False);self.status.setText(self.t('Downloading and verifying …','Download und Prüfung laufen …'))
        self.start('download',self.release,__version__,self.directory)
    def on_progress(self,done,total):
        if self.job and self.job.kind=='download':
            self.progress.setRange(0,100);self.progress.setValue(min(100,100*done//max(1,total)))
    def finish(self):
        self.job=None;self.check_button.setEnabled(True);self.preview.setEnabled(True);self.cancel_button.setEnabled(False);self.progress.hide()
        if self.close_pending:self.close()
    def ready(self,result):
        if not self.job:return
        kind=self.job.kind;self.finish()
        if self.close_pending:return
        if kind=='check':self.checked(result)
        else:
            self.prepared=result;self.folder_button.setEnabled(True)
            message=self.t('Verified update prepared: ','Geprüftes Update vorbereitet: ')+result['version']+'\n'+result['directory']+'\nSHA-256: '+result['sha256']
            message+='\n'+self.t('Close the meter before switching to the new folder. Source packages may require Setup-Meter.cmd. Keep the old folder as a backup. No update has been installed automatically.','Vor dem Wechsel in den neuen Ordner das Meter schließen. Quellcode-Pakete benötigen gegebenenfalls Setup-Meter.cmd. Den alten Ordner als Backup behalten. Es wurde kein Update automatisch installiert.')
            self.status.setText(message)
    def error_message(self,code):return GERMAN_ERRORS.get(code,updates.ERRORS.get(code,code)) if self.language=='de' else updates.ERRORS.get(code,code)
    def failed(self,code):
        self.finish()
        if not self.close_pending:self.status.setText(self.error_message(code))
    def cancel_work(self):
        if self.cancel:self.cancel.set();self.status.setText(self.t('Cancelling …','Wird abgebrochen …'))
    def open_release(self):QDesktopServices.openUrl(QUrl(self.release.page_url if self.release else updates.RELEASES_URL))
    def open_folder(self):
        if self.prepared:QDesktopServices.openUrl(QUrl.fromLocalFile(self.prepared['directory']))
    def closeEvent(self,event):
        if self.job:self.close_pending=True;self.cancel_work();event.ignore();return
        super().closeEvent(event)
