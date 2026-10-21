"""Independent event clock using the meter's existing movable overlay shell."""
import time,uuid
from copy import deepcopy
from PySide6.QtCore import Qt,QTimer,QDateTime,QTimeZone,QRect
from PySide6.QtGui import QPainter,QColor,QFont,QFontMetrics
from PySide6.QtWidgets import (QWidget,QDialog,QVBoxLayout,QHBoxLayout,QLabel,QTableWidget,
    QTableWidgetItem,QPushButton,QCheckBox,QComboBox,QDialogButtonBox,QMessageBox,QSlider,QFormLayout,QScrollArea,QTabWidget)
from .overlay import OverlayWindow
from .events import defaults,validate,schedule,countdown,CATEGORIES,without_irregular_bosses
from .language import text as translated
from .appearance import appearance
from .clock_zones import timezone,zone_id,zone_picker,selected_zone,valid_zone

class EventView(QWidget):
    def __init__(self):
        super().__init__();self.settings={};self.setMinimumSize(240,70)
    def tr_text(self,en,de):return translated(self.settings.get('language','en'),en,de)
    def next_events(self,now):
        try:rows=schedule(self.settings.get('event_schedule',defaults()),now,zone_id(self.settings.get('event_schedule_timezone','Europe/Berlin')))
        except ValueError:return []
        return [row for row in rows if row['start']==rows[0]['start']] if rows else []
    def next_event(self,now):return next(iter(self.next_events(now)),None)
    def event_text(self,now):return '\n'.join(row['name'] for row in self.next_events(now))
    def ui_font(self,offset=0,bold=False):
        theme=appearance(self.settings,'clock')
        return QFont(theme['font_family'],max(7,theme['font_size']+offset),QFont.Weight.Bold if bold else QFont.Weight.Normal)
    def clock_text(self,now):
        zone=timezone(self.settings.get('event_timezone','Europe/Berlin'))
        if not zone.isValid():zone=timezone('Europe/Berlin')
        local=QDateTime.fromSecsSinceEpoch(int(now),zone)
        return local.toString('HH:mm:ss')+' · '+local.timeZoneAbbreviation()
    def text_height(self,text):
        return QFontMetrics(self.ui_font(bold=True)).boundingRect(QRect(0,0,max(1,self.width()-20),10000),Qt.TextFlag.TextWordWrap,text).height()
    def refresh(self):
        scale=appearance(self.settings,'clock')['font_size']/10
        self.setMinimumHeight(max(70,self.text_height(self.event_text(time.time()))+round(54*scale)))
        self.setAccessibleName(self.clock_text(time.time())+' · '+self.event_text(time.time()))
        self.update()
    def resizeEvent(self,event):super().resizeEvent(event);self.refresh()
    def paintEvent(self,event):
        now=time.time();theme=appearance(self.settings,'clock');p=QPainter(self);p.fillRect(self.rect(),QColor(theme['background']))
        font=self.ui_font(-1);p.setFont(font);p.setPen(QColor(theme['text']))
        fm=QFontMetrics(font);clock= fm.elidedText(self.clock_text(now),Qt.TextElideMode.ElideRight,max(1,self.width()-20))
        p.drawText(10,6+fm.ascent(),clock)
        rows=self.next_events(now);top=10+fm.height()
        if not rows:
            p.drawText(QRect(10,top,max(1,self.width()-20),QFontMetrics(self.ui_font()).height()*2),Qt.TextFlag.TextWordWrap,self.tr_text('No events selected','Keine Events gewählt'));return
        p.setPen(QColor(theme['event_text']));p.setFont(self.ui_font(bold=True))
        text='\n'.join(row['name'] for row in rows);height=self.text_height(text)
        p.drawText(QRect(10,top,max(1,self.width()-20),height),Qt.TextFlag.TextWordWrap,text)
        font=self.ui_font(1);p.setFont(font);p.setPen(QColor(theme['countdown']))
        line=self.tr_text('Now','Jetzt') if rows[0]['remaining']==0 else self.tr_text('Starts in ','Start in ')+countdown(rows[0]['remaining'])
        p.drawText(10,top+height+4+QFontMetrics(font).ascent(),line)

class EventOverlay(OverlayWindow):
    minimum_size=(260,115)
    def __init__(self):
        super().__init__();old=self.view;self.view=EventView();self.layout().replaceWidget(old,self.view);old.hide();old.deleteLater()
        for button in self.findChildren(QPushButton):
            if button.objectName()=='resetEncounter':button.hide()
        self.caption.setText('Event Timer');self.tick=QTimer(self);self.tick.setInterval(1000);self.tick.timeout.connect(self.refresh_events);self.tick.start()
    def configure_events(self,settings):
        self.view.settings=deepcopy(settings)
        mapped={**settings,'attached':settings.get('event_attached',False),'opacity':settings.get('event_opacity',settings.get('opacity',88)),'_appearance_section':'clock'}
        for suffix in ('position','free_position','size','locked'):mapped['dps_'+suffix]=settings.get('event_'+suffix,[] if suffix.endswith('position') else False if suffix=='locked' else [300,125])
        super().configure(mapped,settings.get('event_overlay',False));self.translate_controls();self.refresh_events()
    def refresh_events(self):
        self.view.refresh()
        required=self.layout().minimumSize().height()
        if self.locked and required>self.height():
            self.setFixedSize(self.width(),required)
    def translate_controls(self):
        t=self.view.tr_text
        self.caption.setText(t('Event Timer','Event-Uhr'))
        self.lock_button.setText(t('Unlock','Lösen') if self.locked else t('Lock','Fixieren'))
        self.caption.setToolTip(t('Drag to move. Lock freezes position and size.','Zum Verschieben ziehen. Fixieren sperrt Position und Größe.'))
        self.view.setToolTip(t('Clock zone: ','Uhr-Zeitzone: ')+zone_id(self.view.settings.get('event_timezone','Europe/Berlin'))+'\n'+t('Event schedule zone: ','Event-Zeitzone: ')+zone_id(self.view.settings.get('event_schedule_timezone','Europe/Berlin'))+'\n'+t('All events sharing the next start time are shown. Edit appearance and times with the gear button.','Alle Events mit gleicher nächster Startzeit werden angezeigt. Darstellung und Zeiten über das Zahnrad bearbeiten.'))
        for button in self.findChildren(QPushButton):
            if button is not self.lock_button and button.icon().isNull()==False and not button.isHidden():button.setToolTip(t('Clock settings','Uhr-Einstellungen'))
        self.size_grip.setToolTip(t('Resize','Größe ändern'))
    def set_locked(self,locked,emit=True):
        super().set_locked(locked,emit)
        if hasattr(self,'view') and isinstance(self.view,EventView):self.translate_controls()
    def follow_game(self):
        super().follow_game()
        if hasattr(self,'view') and isinstance(self.view,EventView):self.translate_controls()

class EventSettings(QDialog):
    def __init__(self,settings,parent=None):
        super().__init__(parent);self.language=settings.get('language','en');t=self.tr_text
        self.setWindowTitle(t('Clock settings','Uhr-Einstellungen'));self.rows=deepcopy(without_irregular_bosses(settings.get('event_schedule',defaults())))
        layout=QVBoxLayout(self);tabs=QTabWidget();layout.addWidget(tabs)
        scroll=QScrollArea();scroll.setWidgetResizable(True);clock=QWidget();scroll.setWidget(clock);tabs.addTab(scroll,t('Clock','Uhr'));form=QFormLayout(clock)
        self.language_choice=QComboBox();self.language_choice.addItem('English','en');self.language_choice.addItem('Deutsch','de');self.language_choice.setCurrentIndex(1 if self.language=='de' else 0);form.addRow(t('Language','Sprache'),self.language_choice)
        self.show_overlay=QCheckBox(t('Show event timer','Event-Uhr anzeigen'));self.show_overlay.setChecked(settings.get('event_overlay',False));form.addRow(self.show_overlay)
        self.attach=QCheckBox(t('Attach to AION 2','An AION 2 anheften'));self.attach.setChecked(settings.get('event_attached',False));self.attach.setToolTip(t('Follow AION 2 and hide when the game is inactive or closed.','AION 2 folgen und bei inaktivem oder geschlossenem Spiel ausblenden.'));form.addRow(self.attach)
        self.opacity=QSlider(Qt.Orientation.Horizontal);self.opacity.setRange(40,100);self.opacity.setValue(settings.get('event_opacity',settings.get('opacity',88)));form.addRow(t('Clock opacity','Uhr-Deckkraft'),self.opacity)
        self.clock_zone=zone_picker(settings.get('event_timezone','Europe/Berlin'),self.language);form.addRow(t('Clock time zone','Uhr-Zeitzone'),self.clock_zone)
        self.schedule_zone=zone_picker(settings.get('event_schedule_timezone','Europe/Berlin'),self.language);form.addRow(t('Event schedule time zone','Zeitzone der Eventzeiten'),self.schedule_zone)
        note=QLabel(t('The clock zone only changes the displayed time. Event times below use the schedule zone; keep Europe/Berlin for the existing EU schedule. Changing the schedule zone reinterprets those times. Language changes require a restart.','Die Uhr-Zeitzone ändert nur die angezeigte Uhrzeit. Die Eventzeiten gelten in der Event-Zeitzone; für den vorhandenen EU-Plan Europe/Berlin beibehalten. Eine Änderung der Event-Zeitzone interpretiert diese Zeiten neu. Sprachänderungen benötigen einen Neustart.'));note.setWordWrap(True);form.addRow(note)
        from .appearance_editor import AppearanceEditor
        self.appearance=AppearanceEditor(settings,('clock',),self.language);appearance_scroll=QScrollArea();appearance_scroll.setWidgetResizable(True);appearance_scroll.setWidget(self.appearance);tabs.addTab(appearance_scroll,t('Appearance','Darstellung'))
        self.clock_zone.currentTextChanged.connect(self.preview_zones);self.schedule_zone.currentTextChanged.connect(self.preview_zones)
        events=QWidget();events_layout=QVBoxLayout(events);tabs.addTab(events,t('Events','Events'))
        hint=QLabel(t('Times use the event schedule time zone selected on the first tab. Days: 1=Mon to 7=Sun. Events sharing a start time appear together. Siege and scheduled Abyss bosses remain included; irregular world bosses are excluded.','Die Zeiten gelten in der Event-Zeitzone des ersten Tabs. Tage: 1=Mo bis 7=So. Events mit gleicher Startzeit erscheinen gemeinsam. Belagerung und feste Abyss-Bosszeiten bleiben enthalten; unregelmäßige Worldbosse entfallen.'));hint.setWordWrap(True);events_layout.addWidget(hint)
        self.table=QTableWidget(0,6);self.table.setHorizontalHeaderLabels([t('On','An'),'Event',t('Type','Art'),t('Start times HH:mm','Startzeiten HH:mm'),t('Days 1–7','Tage 1–7'),t('Window min','Fenster min')]);events_layout.addWidget(self.table)
        for row in self.rows:self.add_row(row)
        self.table.setColumnHidden(5,True)
        actions=QHBoxLayout();add=QPushButton(t('Add event','Event hinzufügen'));add.clicked.connect(lambda:self.add_row(dict(id=uuid.uuid4().hex,name=t('Custom event','Eigenes Event'),category='Sonstiges',times=[],days=list(range(7)),minutes=0,enabled=False,status='user',source='user')));actions.addWidget(add)
        remove=QPushButton(t('Remove selected','Auswahl entfernen'));remove.clicked.connect(self.remove_row);actions.addWidget(remove);events_layout.addLayout(actions)
        self.error=QLabel();self.error.setWordWrap(True);layout.addWidget(self.error)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel);buttons.accepted.connect(self.submit);buttons.rejected.connect(self.reject);layout.addWidget(buttons)
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(t('Cancel','Abbrechen'))
        self.setStyleSheet('QDialog,QWidget{background:#17242e;color:#dce9f2;} QTableWidget,QLineEdit,QComboBox{background:#243b49;color:#dce9f2;} QPushButton{padding:6px;}')
        screen=self.screen();self.resize(850,min(720,screen.availableGeometry().height()-60) if screen else 650);self.table.setColumnWidth(1,190);self.table.setColumnWidth(3,230)
    def preview_zones(self,*args):
        self.appearance.settings.update(event_timezone=selected_zone(self.clock_zone),event_schedule_timezone=selected_zone(self.schedule_zone))
        self.appearance.refresh_preview('clock')
    def tr_text(self,en,de):return translated(self.language,en,de)
    def add_row(self,row):
        i=self.table.rowCount()
        if i>=60:return
        self.table.insertRow(i);check=QTableWidgetItem();check.setFlags(Qt.ItemFlag.ItemIsEnabled|Qt.ItemFlag.ItemIsUserCheckable);check.setCheckState(Qt.CheckState.Checked if row['enabled'] else Qt.CheckState.Unchecked);check.setData(Qt.ItemDataRole.UserRole,deepcopy(row));check.setToolTip(str(row.get('source','')));self.table.setItem(i,0,check)
        self.table.setItem(i,1,QTableWidgetItem(row['name']));choice=QComboBox()
        for category in CATEGORIES:choice.addItem(self.tr_text('Other','Sonstiges') if category=='Sonstiges' else category,category)
        choice.setCurrentIndex(CATEGORIES.index(row['category']));self.table.setCellWidget(i,2,choice)
        for col,text in [(3,', '.join(row['times'])),(4,','.join(str(d+1) for d in row['days'])),(5,str(row['minutes']))]:self.table.setItem(i,col,QTableWidgetItem(text))
    def remove_row(self):
        i=self.table.currentRow()
        if i>=0:self.table.removeRow(i)
    def submit(self):
        try:
            self.result_timezone=selected_zone(self.clock_zone);self.result_schedule_timezone=selected_zone(self.schedule_zone)
            if not valid_zone(self.result_timezone) or not valid_zone(self.result_schedule_timezone):raise ValueError(self.tr_text('Select a valid time zone.','Eine gültige Zeitzone auswählen.'))
            self.result_appearance=self.appearance.result()
            rows=[]
            for i in range(self.table.rowCount()):
                item=self.table.item(i,0);old=item.data(Qt.ItemDataRole.UserRole);row=deepcopy(old)
                row.update(enabled=item.checkState()==Qt.CheckState.Checked,name=self.table.item(i,1).text().strip(),category=self.table.cellWidget(i,2).currentData(),times=[t.strip() for t in self.table.item(i,3).text().split(',') if t.strip()],days=[int(d.strip())-1 for d in self.table.item(i,4).text().split(',') if d.strip()],minutes=int(self.table.item(i,5).text()))
                if any(row[k]!=old.get(k) for k in ('name','category','times','days','minutes')):row.update(source='user',status='user',checked=QDateTime.currentDateTimeUtc().toString('yyyy-MM-dd'))
                rows.append(row)
            self.result_rows=validate(rows,self.language)
        except (ValueError,TypeError) as exc:
            self.error.setText(str(exc) if isinstance(exc,ValueError) and 'invalid literal' not in str(exc) else self.tr_text('Enter valid numbers for days.','Gültige Zahlen für die Tage eingeben.'));return
        self.accept()
