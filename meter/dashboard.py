"""User-facing compact live meter and independent overlays; see LICENSE-STATUS.md."""
from .language import tr as _tr
import os
from pathlib import Path
from PySide6.QtCore import Qt,QTimer,QUrl
from PySide6.QtGui import QColor,QFont,QFontDatabase,QDesktopServices
from PySide6.QtWidgets import (QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,
    QCheckBox,QDialog,QDialogButtonBox,QFormLayout,QComboBox,QSlider,QFileDialog,QColorDialog,QInputDialog,QSpinBox,QMenu,QApplication,QScrollArea,QLayout,QTabWidget,QGridLayout,QGroupBox)
from .worker import MeterWorker,BASE
from .overlay import DamageView,OverlayWindow,CLASS_COLORS,number
from .preferences import Preferences,runtime_directory
from . import diagnostics
from .combat_logs import CombatLogWriter
from .details import PlayerDetails,FightHistory
from .core.skill_labels import SkillLabels

class SettingsDialog(QDialog):
    """One settings window with independent behavior/design pages per overlay."""
    def __init__(self,settings,directory,parent=None):
        super().__init__(parent)
        from .language import text
        from .appearance_editor import AppearanceEditor
        from .event_overlay import EventSettings
        self.t=lambda en,de:text(settings.get('language','en'),en,de)
        t=self.t;self.setWindowTitle(t('Settings','Einstellungen'))
        self.values=dict(settings);self.values['class_colors']=dict(settings.get('class_colors',{}))
        outer=QVBoxLayout(self);self.tabs=QTabWidget();outer.addWidget(self.tabs)
        self.section_pages={};self.section_tabs={};self.checks={}
        def form_page(tabs,label):
            scroll=QScrollArea();scroll.setWidgetResizable(True);body=QWidget();scroll.setWidget(body)
            layout=QVBoxLayout(body);form=QFormLayout();form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows);layout.addLayout(form);layout.addStretch(1)
            tabs.addTab(scroll,label);return scroll,form
        self.global_page,global_form=form_page(self.tabs,'Global');self.section_pages['global']=self.global_page
        self.language_choice=QComboBox();self.language_choice.addItem('English','en');self.language_choice.addItem('Deutsch','de');self.language_choice.setCurrentIndex(1 if settings.get('language')=='de' else 0);global_form.addRow(t('Language','Sprache'),self.language_choice)
        hint=QLabel(_tr('Sprachänderungen gelten nach einem Meter-Neustart.'));hint.setWordWrap(True);global_form.addRow(hint)
        for key,label in [('click_through',_tr('Maus durch Overlay durchreichen')),('track_pvp',_tr('Gegnerischen PvP-Schaden erfassen')),('skill_names_enabled',_tr('Lokale Skillnamen laden')),('manual_identity',_tr('Manuelle Charakterzuordnung anzeigen (Diagnose)'))]:
            box=QCheckBox(label);box.setChecked(settings[key]);self.checks[key]=box;global_form.addRow(box)
        # Keep stable attachment data, while exposing independent switches.
        self.attachment=QComboBox(self)
        for key in ('Frei schwebend','Beide an AION 2','Nur DPS an AION 2','Nur Graph an AION 2'):self.attachment.addItem(_tr(key),key)
        self.attachment.setCurrentIndex(max(0,self.attachment.findData(settings.get('attachment_mode','Frei schwebend'))));self.attachment.hide()
        self.appearance=AppearanceEditor(settings,('dps','graph'),settings.get('language','en'),self)
        self.geometry_controls={};self.attach_checks={}
        for section,label,default in [('dps',t('DPS / healing','DPS / Heilung'),[350,260]),('graph',t('Graph','Graph'),[350,220])]:
            category=QWidget();category_layout=QVBoxLayout(category);category_layout.setContentsMargins(0,0,0,0);sub=QTabWidget();category_layout.addWidget(sub)
            self.tabs.addTab(category,label);self.section_pages[section]=category;self.section_tabs[section]=sub
            scroll,form=form_page(sub,t('Settings','Einstellungen'))
            enable=QCheckBox(_tr('DPS-Overlay') if section=='dps' else _tr('DPS-Graph als Overlay'));key='overlay' if section=='dps' else 'graph_overlay';enable.setChecked(settings[key]);self.checks[key]=enable;form.addRow(enable)
            attach=QCheckBox(_tr('An AION 2 anheften'));self.attach_checks[section]=attach;form.addRow(attach)
            tip=QLabel(t('Attached overlays follow AION 2 and hide outside the active game. Free-floating overlays remain visible independently of the main window.','Angeheftete Overlays folgen AION 2 und verschwinden außerhalb des aktiven Spiels. Frei schwebende Overlays bleiben unabhängig vom Hauptfenster sichtbar.'));tip.setWordWrap(True);form.addRow(tip)
            lock=QCheckBox(t('Lock position and size','Position und Größe fixieren'));lock.setChecked(settings[section+'_locked']);self.checks[section+'_locked']=lock;form.addRow(lock)
            opacity=QSlider(Qt.Orientation.Horizontal);opacity.setRange(40,100);opacity.setValue(settings.get('graph_opacity',settings['opacity']) if section=='graph' else settings['opacity']);form.addRow(t('Opacity','Deckkraft'),opacity)
            if section=='dps':self.opacity=opacity
            else:self.graph_opacity=opacity
            row=QHBoxLayout();controls=[]
            for index,unit in enumerate((_tr('Breite'),_tr('Höhe'))):
                spin=QSpinBox();spin.setRange(280 if index==0 else 180,2400 if index==0 else 1600);spin.setValue(settings.get(section+'_size',default)[index]);spin.setSuffix(' px');spin.setAccessibleName(label+' '+unit);controls.append(spin);row.addWidget(spin)
            self.geometry_controls[section]=controls;form.addRow(t('Size','Größe'),row)
            if section=='dps':
                self.dps_font=QSpinBox();self.dps_font.setRange(8,24);self.dps_font.setValue(settings.get('dps_font_size',14));self.dps_font.setSuffix(' pt');form.addRow(_tr('DPS-Zahlen'),self.dps_font)
            page=self.appearance.pages[section];index=self.appearance.tabs.indexOf(page);self.appearance.tabs.removeTab(index)
            design_scroll=QScrollArea();design_scroll.setWidgetResizable(True);design_scroll.setWidget(page);sub.addTab(design_scroll,t('Design','Design'))
        self.appearance.hide()
        self.palette=QComboBox()
        for key in ('Klassenfarben','Neon','Pastell','Barrierearm','Einfarbig'):self.palette.addItem(_tr(key),key)
        self.palette.setCurrentIndex(max(0,self.palette.findData(settings['palette'])))
        form=self.appearance.forms['dps'];form.insertRow(0,_tr('Farben'),self.palette)
        accent=QPushButton(_tr('Akzentfarbe wählen'));accent.clicked.connect(self.choose_accent);form.insertRow(1,accent)
        colors=QHBoxLayout();self.class_choice=QComboBox();self.class_choice.addItems(list(CLASS_COLORS));change=QPushButton(_tr('Klassenfarbe'));change.clicked.connect(self.choose_class);colors.addWidget(self.class_choice);colors.addWidget(change);form.insertRow(2,colors)
        self.palette.currentIndexChanged.connect(self.refresh_palette_preview)
        self.attachment.currentIndexChanged.connect(self.sync_attach_checks);self.sync_attach_checks()
        for checkbox in self.attach_checks.values():checkbox.toggled.connect(self.update_attachment)
        # Reuse the clock editor/validation, but move its pages into this window.
        self.clock_editor=EventSettings(settings,self);self.clock_editor.hide();self.clock_tabs=self.clock_editor.findChild(QTabWidget)
        self.clock_editor.layout().removeWidget(self.clock_tabs);clock_page=QWidget();clock_layout=QVBoxLayout(clock_page);clock_layout.setContentsMargins(0,0,0,0);clock_layout.addWidget(self.clock_tabs)
        clock_design=self.clock_tabs.widget(1);clock_appearance=self.clock_editor.appearance
        clock_design.takeWidget();clock_appearance.setParent(self.clock_editor);clock_appearance.hide()
        clock_content=clock_appearance.pages['clock'];clock_appearance.tabs.removeTab(0);clock_design.setWidget(clock_content)
        self.clock_tabs.setTabText(0,t('Settings','Einstellungen'));self.clock_tabs.setTabText(1,t('Design','Design'));self.tabs.addTab(clock_page,t('Clock','Uhr'));self.section_pages['clock']=clock_page;self.section_tabs['clock']=self.clock_tabs
        language_label=self.clock_editor.language_choice.parentWidget().layout().labelForField(self.clock_editor.language_choice)
        if language_label:language_label.hide()
        self.clock_editor.language_choice.hide();self.language_choice.currentIndexChanged.connect(self.clock_editor.language_choice.setCurrentIndex)
        logs,log_form=form_page(self.tabs,t('Logs','Logs'));self.section_pages['logs']=logs
        for key,label in [('save_combat',_tr('Kampflogs speichern (JSON)')),('save_debug',_tr('Fehlerprotokolle speichern')),('save_packets',_tr('Paketmitschnitte speichern (Analyse)'))]:
            box=QCheckBox(label);box.setChecked(settings[key]);self.checks[key]=box;log_form.addRow(box)
        self.folder=settings['log_folder'] or str(Path(directory)/'sessions');self.folder_button=QPushButton(_tr('Log-Ordner wählen'));self.folder_button.clicked.connect(self.choose_folder);log_form.addRow(self.folder_button)
        self.path_label=QLabel(self.folder);self.path_label.setWordWrap(True);log_form.addRow(self.path_label)
        config=QLabel(str(Path(directory)/'preferences.json'));config.setWordWrap(True);config.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse);log_form.addRow(_tr('Konfiguration'),config)
        self.error=QLabel();self.error.setWordWrap(True);outer.addWidget(self.error)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel);buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject);buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(t('Cancel','Abbrechen'));outer.addWidget(buttons)
        self.setStyleSheet('QDialog,QWidget{background:#17242e;color:#dce9f2;font:10pt "Segoe UI";} QComboBox,QSpinBox,QLineEdit{background:#243b49;color:#dce9f2;} QPushButton{padding:6px;}')
        screen=QApplication.primaryScreen();self.resize(880,min(760,screen.availableGeometry().height()-60) if screen else 700)
    def select_section(self,section='global',page='settings'):
        if section in self.section_pages:self.tabs.setCurrentWidget(self.section_pages[section])
        if section in self.section_tabs:self.section_tabs[section].setCurrentIndex(1 if page=='design' else 0)
    def sync_attach_checks(self,*args):
        mode=self.attachment.currentData()
        for section,box in self.attach_checks.items():
            box.blockSignals(True);box.setChecked(mode=='Beide an AION 2' or mode==('Nur DPS an AION 2' if section=='dps' else 'Nur Graph an AION 2'));box.blockSignals(False)
    def update_attachment(self,*args):
        dps=self.attach_checks['dps'].isChecked();graph=self.attach_checks['graph'].isChecked()
        mode='Beide an AION 2' if dps and graph else 'Nur DPS an AION 2' if dps else 'Nur Graph an AION 2' if graph else 'Frei schwebend'
        self.attachment.setCurrentIndex(self.attachment.findData(mode))
    def refresh_palette_preview(self,*args):
        self.appearance.settings.update(palette=self.palette.currentData(),accent=self.values['accent'],class_colors=dict(self.values['class_colors']));self.appearance.refresh_preview('dps')
    def choose_accent(self):
        color=QColorDialog.getColor(QColor(self.values['accent']),self,_tr('Akzentfarbe'))
        if color.isValid():self.values['accent']=color.name();self.refresh_palette_preview()
    def choose_class(self):
        cls=self.class_choice.currentText();color=QColorDialog.getColor(QColor(self.values['class_colors'].get(cls,CLASS_COLORS[cls])),self,cls)
        if color.isValid():self.values['class_colors'][cls]=color.name();self.refresh_palette_preview()
    def choose_folder(self):
        folder=QFileDialog.getExistingDirectory(self,_tr('Kampflog-Ordner'),self.folder)
        if folder:self.folder=folder;self.path_label.setText(folder)
    def accept(self):
        self.clock_editor.setResult(QDialog.DialogCode.Rejected);self.clock_editor.submit()
        if self.clock_editor.result()!=QDialog.DialogCode.Accepted:
            self.error.setText(self.clock_editor.error.text());self.select_section('clock');return
        super().accept()
    def result_settings(self):
        from .clock_zones import selected_zone
        styles=self.appearance.result();styles['clock']=self.clock_editor.appearance.result()['clock']
        return {**self.values,'language':self.language_choice.currentData(),'palette':self.palette.currentData(),'opacity':self.opacity.value(),'graph_opacity':self.graph_opacity.value(),'appearance':styles,
                'event_schedule':getattr(self.clock_editor,'result_rows',self.values['event_schedule']),'event_overlay':self.clock_editor.show_overlay.isChecked(),'event_attached':self.clock_editor.attach.isChecked(),'event_opacity':self.clock_editor.opacity.value(),
                'event_timezone':selected_zone(self.clock_editor.clock_zone),'event_schedule_timezone':selected_zone(self.clock_editor.schedule_zone),
                'log_folder':self.folder,'attachment_mode':self.attachment.currentData(),'dps_font_size':self.dps_font.value(),
                **{prefix+'_size':[control.value() for control in controls] for prefix,controls in self.geometry_controls.items()},**{key:box.isChecked() for key,box in self.checks.items()}}

class LiveDashboard(QMainWindow):
    def __init__(self,auto_start=True,data_dir=None):
        super().__init__()
        for filename in ('segoeui.ttf','consola.ttf'):
            font=Path(os.environ.get('WINDIR',r'C:\Windows'))/'Fonts'/filename
            if font.is_file():QFontDatabase.addApplicationFont(str(font))
        self.setWindowTitle(_tr('AION 2 · Live DPS'))
        self.resize(550,500);self.setMinimumSize(470,420)
        self.data_dir=Path(data_dir) if data_dir else runtime_directory(BASE)
        self.preferences=Preferences(self.data_dir);self.settings=self.preferences.values;self.preferences.save()
        from .language import set_language
        set_language(self.settings['language'])
        self.skill_labels=SkillLabels.for_runtime(self.data_dir,self.settings)
        self.log_writer=CombatLogWriter(self.settings['log_folder'] or self.data_dir/'sessions')
        diagnostics.set_enabled(self.settings['save_debug'],self.data_dir)
        self.worker=None;self.workers=[];self.latest={'fights':[]};self.saved={};self.closing=False;self.details=[];self.display_floor=0;self.history_dialogs=[]
        self.overlay=OverlayWindow();self.graph_overlay=OverlayWindow(True)
        from .event_overlay import EventOverlay
        self.event_overlay=EventOverlay()
        self.event_overlay.closed.connect(self.hide_event_overlay)
        for signal,key in [(self.event_overlay.positionChanged,'event_position'),(self.event_overlay.freePositionChanged,'event_free_position'),(self.event_overlay.sizeChanged,'event_size')]:
            signal.connect(lambda value,k=key:self.save_overlay_position(k,value))
        self.event_overlay.lockChanged.connect(lambda value:self.set_overlay_lock('event_locked',value))
        self.event_overlay.optionsRequested.connect(self.configure_events)
        self.overlay.closed.connect(lambda:self.disable_overlay('overlay'))
        self.graph_overlay.closed.connect(lambda:self.disable_overlay('graph_overlay'))
        self.overlay.positionChanged.connect(lambda position:self.save_overlay_position('dps_position',position))
        self.graph_overlay.positionChanged.connect(lambda position:self.save_overlay_position('graph_position',position))
        self.overlay.freePositionChanged.connect(lambda position:self.save_overlay_position('dps_free_position',position))
        self.graph_overlay.freePositionChanged.connect(lambda position:self.save_overlay_position('graph_free_position',position))
        self.overlay.sizeChanged.connect(lambda size:self.save_overlay_position('dps_size',size))
        self.graph_overlay.sizeChanged.connect(lambda size:self.save_overlay_position('graph_size',size))
        self.overlay.lockChanged.connect(lambda value:self.set_overlay_lock('dps_locked',value))
        self.graph_overlay.lockChanged.connect(lambda value:self.set_overlay_lock('graph_locked',value))
        self.overlay.view.actorClicked.connect(self.show_actor_details)
        for section,pane in (('dps',self.overlay),('graph',self.graph_overlay)):
            pane.resetRequested.connect(self.reset_fight);pane.optionsRequested.connect(lambda s=section:self.configure(s))
        from .language import text
        t=lambda en,de:text(self.settings['language'],en,de)
        root=QWidget();root.setObjectName('dashboardRoot');self.content_scroll=QScrollArea();self.content_scroll.setWidgetResizable(True);self.content_scroll.setWidget(root);self.setCentralWidget(self.content_scroll)
        layout=QVBoxLayout(root);layout.setContentsMargins(18,18,18,14);layout.setSpacing(14)
        top=QHBoxLayout();branding=QVBoxLayout();title=QLabel('AION 2');title.setObjectName('title');branding.addWidget(title)
        subtitle=QLabel(t('Combat overview','Kampfübersicht'));subtitle.setObjectName('muted');branding.addWidget(subtitle);top.addLayout(branding);top.addStretch()
        self.live_badge=QLabel('LIVE');self.live_badge.setObjectName('badge');top.addWidget(self.live_badge,0,Qt.AlignmentFlag.AlignVCenter)
        setup=QPushButton(t('Settings','Einstellungen'));setup.setToolTip(_tr('Farben, Overlay und Logspeicher'));setup.clicked.connect(self.configure);top.addWidget(setup);layout.addLayout(top)
        connection=QHBoxLayout();self.status=QLabel(_tr('Verbindet automatisch mit AION 2 …'));self.status.setWordWrap(True);connection.addWidget(self.status,1)
        self.capture_button=QPushButton(_tr('Live pausieren'));self.capture_button.clicked.connect(self.toggle_capture);connection.addWidget(self.capture_button);layout.addLayout(connection)
        self.main_tabs=QTabWidget();layout.addWidget(self.main_tabs,1)
        def page(label):
            widget=QWidget();body=QVBoxLayout(widget);body.setContentsMargins(12,16,12,12);body.setSpacing(12);self.main_tabs.addTab(widget,label);return widget,body
        live,live_layout=page(t('Live','Live'));self.live_page=live
        self.summary=QLabel(_tr('0 Schaden  ·  0 Ø DPS  ·  0:00'));self.summary.setObjectName('summary');self.summary.setWordWrap(True);live_layout.addWidget(self.summary)
        from .metrics import METRICS
        metric_bar=QHBoxLayout();metric_bar.addWidget(QLabel(_tr('Auswertung')));self.metric_choice=QComboBox()
        for key,label in METRICS.items():self.metric_choice.addItem(label,key)
        self.metric_choice.setCurrentIndex(self.metric_choice.findData(self.settings['display_metric']));self.metric_choice.setToolTip(_tr('Heilung ist beobachtete Protokollheilung; effektive Heilung und Überheilung sind nicht bestätigt. Fremdheilung: an andere Entities.'));self.metric_choice.currentIndexChanged.connect(self.change_metric);metric_bar.addWidget(self.metric_choice,1);live_layout.addLayout(metric_bar)
        from .encounter_scope import scope_label
        self.scope_controls=QWidget();scope_layout=QHBoxLayout(self.scope_controls);scope_layout.setContentsMargins(0,0,0,0);scope_layout.addWidget(QLabel(_tr('Dungeon-Ziele')));self.scope_choice=QComboBox()
        for key in ('all','boss','trash','unknown'):self.scope_choice.addItem(scope_label(key),key)
        self.scope_choice.setCurrentIndex(max(0,self.scope_choice.findData(self.settings['dungeon_scope'])));scope_layout.addWidget(self.scope_choice,1);self.scope_choice.currentIndexChanged.connect(self.change_dungeon_scope);live_layout.addWidget(self.scope_controls);self.scope_controls.hide()
        self.view=DamageView();self.view.setMinimumHeight(230);self.view.actorClicked.connect(self.show_actor_details);live_layout.addWidget(self.view,1)
        self.group_status=QLabel('');self.group_status.setWordWrap(True);self.group_status.setObjectName('muted');live_layout.addWidget(self.group_status)
        actions=QGridLayout();actions.setHorizontalSpacing(10);actions.setVerticalSpacing(8)
        new=QPushButton(_tr('Neuer Kampf'));new.clicked.connect(self.reset_fight);actions.addWidget(new,0,0)
        past=QPushButton(_tr('Kampfverlauf'));past.clicked.connect(self.show_history);actions.addWidget(past,0,1)
        self.chat_copy=QPushButton(_tr('Chattext kopieren'));self.chat_copy.setToolTip(_tr('Gruppenschaden des angezeigten Kampfes in die Zwischenablage kopieren'));self.chat_copy.clicked.connect(self.copy_chat);actions.addWidget(self.chat_copy,1,0)
        from .export_job import ExportController
        self.export_controller=ExportController(self);self.dungeon_log_button=QPushButton(_tr('Dungeon kopieren'));self.dungeon_log_button.setObjectName('primaryAction');self.dungeon_log_button.setToolTip(_tr('Bosskämpfe dieses Dungeons als teilbaren Chattext kopieren'));self.dungeon_log_button.clicked.connect(self.copy_dungeon_log);actions.addWidget(self.dungeon_log_button,1,1);live_layout.addLayout(actions)
        overlays,overlay_layout=page(t('Overlays','Overlays'));self.overlays_page=overlays
        def card(parent,title,description):
            box=QGroupBox(title);body=QVBoxLayout(box);body.setSpacing(12);label=QLabel(description);label.setObjectName('muted');label.setWordWrap(True);body.addWidget(label);parent.addWidget(box);return body
        quick=card(overlay_layout,t('Visibility','Sichtbarkeit'),t('Show each overlay independently. Appearance and behavior are available in Settings.','Jedes Overlay einzeln einblenden. Darstellung und Verhalten findest du in den Einstellungen.'))
        self.overlay_toggle=QCheckBox(_tr('DPS-Overlay'));self.overlay_toggle.setChecked(self.settings['overlay']);self.graph_toggle=QCheckBox(_tr('Graph-Overlay'));self.graph_toggle.setChecked(self.settings['graph_overlay']);self.event_toggle=QCheckBox(t('Event clock','Event-Uhr'));self.event_toggle.setChecked(self.settings['event_overlay'])
        for box,key,section in [(self.overlay_toggle,'overlay','dps'),(self.graph_toggle,'graph_overlay','graph'),(self.event_toggle,'event_overlay','clock')]:
            row=QHBoxLayout();row.addWidget(box,1);button=QPushButton(t('Customize','Anpassen'));button.clicked.connect(lambda checked=False,s=section:self.configure(s,'design'));row.addWidget(button);quick.addLayout(row);box.toggled.connect(lambda value,k=key:self.change_option(k,value))
            if section=='clock':self.event_options=button
        positioning=card(overlay_layout,t('Position and attachment','Position und Anheften'),t('Attached overlays follow the active AION 2 window. Use Settings for independent sizes and positions.','Angeheftete Overlays folgen dem aktiven AION-2-Fenster. Einzelne Größen und Positionen findest du in den Einstellungen.'))
        self.attach_toggle=QComboBox()
        for key in ['Frei schwebend','Beide an AION 2','Nur DPS an AION 2','Nur Graph an AION 2']:self.attach_toggle.addItem(_tr(key),key)
        self.attach_toggle.setToolTip(_tr('Anheften: dem Spielfenster folgen und außerhalb des Spiels ausblenden. Gilt für DPS und Graph gemäß Auswahl.'));self.attach_toggle.setCurrentIndex(max(0,self.attach_toggle.findData(self.settings['attachment_mode'])));self.attach_toggle.currentIndexChanged.connect(lambda index:self.change_option('attachment_mode',self.attach_toggle.currentData()));positioning.addWidget(self.attach_toggle)
        self.lock_toggle=QPushButton(_tr('Fixieren'));self.lock_toggle.setCheckable(True);self.lock_toggle.toggled.connect(self.set_all_locks);positioning.addWidget(self.lock_toggle);overlay_layout.addStretch()
        tools,tools_layout=page(t('Tools','Werkzeuge'));self.tools_page=tools
        logs_card=card(tools_layout,t('Logs and files','Logs und Dateien'),t('Review saved fights, share diagnostics or open the storage folders.','Gespeicherte Kämpfe ansehen, Diagnosen teilen oder Speicherordner öffnen.'))
        grid=QGridLayout();logs_card.addLayout(grid)
        logs=QPushButton(_tr('Logs öffnen'));menu=QMenu(logs);menu.addAction(_tr('Kampflogs (JSON)'),lambda:self.open_path(self.combat_directory()));menu.addAction(_tr('Fehlerprotokolle'),lambda:self.open_path(self.data_dir/'logs'));logs.setMenu(menu);grid.addWidget(logs,0,0)
        packets=QPushButton(_tr('Mitschnitte'));packets.clicked.connect(lambda:self.open_path(self.data_dir/'captures'));grid.addWidget(packets,0,1)
        config=QPushButton('Config');config.clicked.connect(lambda:self.open_path(self.preferences.path,True));grid.addWidget(config,1,0)
        browser=QPushButton(_tr('Log-Verwaltung'));browser.clicked.connect(self.show_log_browser);grid.addWidget(browser,1,1)
        support=card(tools_layout,t('Diagnostics','Diagnose'),t('Inspect capture quality or create a support export.','Erfassungsqualität prüfen oder einen Diagnoseexport erstellen.'))
        row=QHBoxLayout();support.addLayout(row)
        for label,callback in ((_tr('Datenqualität'),self.show_quality),(_tr('Diagnose exportieren'),self.show_support)):
            button=QPushButton(label);button.clicked.connect(callback);row.addWidget(button)
        self.identity_button=QPushButton(_tr('Eigenen Charakter zuordnen'));self.identity_button.clicked.connect(self.choose_self);self.identity_button.setVisible(self.settings.get('manual_identity',False));support.addWidget(self.identity_button)
        collection=card(tools_layout,t('Collection','Sammlung'),t('Keep track of your pet checklist.','Deine Pet-Checkliste im Blick behalten.'));self.pets_button=QPushButton(_tr('Pet-Checkliste'));self.pets_button.clicked.connect(self.show_pets);collection.addWidget(self.pets_button);tools_layout.addStretch()
        self.notice=QLabel('');self.notice.setWordWrap(True);self.notice.setObjectName('notice');layout.addWidget(self.notice)
        self.storage_status=QLabel();self.storage_status.setObjectName('muted');self.storage_status.setWordWrap(True);layout.addWidget(self.storage_status)
        self.timer=QTimer(self);self.timer.setInterval(500);self.timer.timeout.connect(self.poll);self.timer.start()
        self.resize(*self.settings['window_size'])
        position=self.settings.get('window_position',[])
        if len(position)==2:
            point=self.overlay.visible_position(position,self.size());self.move(point)
        self.apply_overlay_settings();self.update_storage_status()
        if auto_start:QTimer.singleShot(0,self.start_live)
    def display_report(self):
        report=self.latest if not self.display_floor else {**self.latest,'fights':[f for f in self.latest.get('fights',[]) if f['id']>self.display_floor]}
        scope=self.settings.get('dungeon_scope','all');fights=report.get('fights',[])
        if scope=='all' or not fights or not fights[-1].get('dungeon_name'):return report
        cache=getattr(self,'_scope_input',None)
        if cache and cache[0] is self.latest and cache[1:]==(self.display_floor,scope):return self._scope_output
        from .encounter_scope import project_report
        projected=None
        for fight in reversed(fights):
            if fight.get('run_key')!=fights[-1].get('run_key'):continue
            projected=project_report({**report,'fights':[fight]},scope)
            if projected:break
        self._scope_input=(self.latest,self.display_floor,scope);self._scope_output=projected or {**report,'fights':[]}
        return self._scope_output
    def change_dungeon_scope(self,*args):
        self.settings['dungeon_scope']=self.scope_choice.currentData();self.preferences.save();self.render()
    def change_metric(self,index):
        self.settings['display_metric']=self.metric_choice.currentData();self.preferences.save();self.render()
    def copy_chat(self):
        from PySide6.QtWidgets import QApplication
        from .chat_export import fight_text,healing_text
        mode=self.settings.get('display_metric','damage')
        text=fight_text(self.display_report()) if mode=='damage' else healing_text(self.display_report(),mode)
        if text:
            QApplication.clipboard().setText(text)
            self.notice.setText(_tr('Chattext kopiert – im Spiel einfügen.'))
        else:self.notice.setText(_tr('Noch kein Kampf zum Kopieren vorhanden.'))
    def copy_dungeon_log(self):
        from .chat_export import run_identity
        selected=self.display_report()
        if run_identity(selected) is None:
            self.notice.setText(_tr('Noch keine erkannte Dungeon-Zuordnung zum Kopieren.'));return
        self.export_controller.start(self.combat_directory(),self.latest,selected,'',self.notice,self.dungeon_log_button,output='chat')

    def reset_fight(self):
        if self.worker:
            with self.worker.session.lock:
                ledger=self.worker.session.core.ledger;ledger.finish('manual_reset');ledger.capture_partial=True
            self.worker.emit_snapshot(True);self.latest=self.worker.last_report
        self.display_floor=max((f['id'] for f in self.latest.get('fights',[])),default=0);self.render()
    def show_actor_details(self,actor):
        report=self.display_report()
        if not report.get('fights') or not any(a['id']==actor for a in report['fights'][-1]['actors']):return
        dialog=PlayerDetails(report,actor,self);self.details.append(dialog);dialog.destroyed.connect(lambda:self.forget_detail(dialog));dialog.show()
    def show_pets(self):
        from .pets import PetChecklist
        if not hasattr(self,'pet_dialog'):self.pet_dialog=PetChecklist(self.preferences,self)
        self.pet_dialog.render();self.pet_dialog.show();self.pet_dialog.raise_();self.pet_dialog.activateWindow()
    def show_quality(self):
        from .quality_dialog import QualityDialog
        dialog=QualityDialog(self.display_report(),self);self.details.append(dialog);dialog.destroyed.connect(lambda:self.forget_detail(dialog));dialog.show()
    def show_log_browser(self):
        from .log_browser import LogBrowser
        dialog=LogBrowser(self.combat_directory(),self.data_dir,self.latest,self.preferences,self);self.history_dialogs.append(dialog);dialog.destroyed.connect(lambda:self.forget_history(dialog));dialog.show()
    def show_support(self):
        from .support_dialog import SupportDialog
        dialog=SupportDialog(self.latest,self.settings,self.data_dir,self);self.history_dialogs.append(dialog);dialog.destroyed.connect(lambda:self.forget_history(dialog));dialog.show()
    def forget_detail(self,dialog):
        if dialog in self.details:self.details.remove(dialog)
    def show_history(self):
        dialog=FightHistory(self.latest,self.combat_directory(),self);self.history_dialogs.append(dialog);dialog.destroyed.connect(lambda:self.forget_history(dialog));dialog.show()
    def forget_history(self,dialog):
        if dialog in self.history_dialogs:self.history_dialogs.remove(dialog)
    def combat_directory(self):return Path(self.settings['log_folder']) if self.settings['log_folder'] else self.data_dir/'sessions'
    def open_path(self,path,is_file=False):
        path=Path(path)
        try:
            if is_file:self.preferences.save()
            else:path.mkdir(parents=True,exist_ok=True)
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.resolve()))):self.notice.setText(_tr('Ordner/Datei konnte nicht geöffnet werden: ')+str(path))
        except OSError as error:self.notice.setText(str(error))
    def update_storage_status(self):
        state=self.latest.get('storage',{});error=state.get('combat_error') or state.get('packet_error')
        if error:self.storage_status.setText(_tr('Speicherfehler: ')+error)
        else:
            combat=state.get('combat_enabled',self.settings['save_combat']);packets=state.get('packet_enabled',self.settings['save_packets'])
            self.storage_status.setText(_tr('Kampflogs: ')+_tr('an' if combat else 'aus')+_tr(' · Mitschnitt: ')+_tr('an' if packets else 'aus'))
        self.storage_status.setToolTip(_tr('Kampflogs: ')+str(self.combat_directory())+_tr('\nMitschnitte: ')+str(self.data_dir/'captures')+_tr('\nKonfiguration: ')+str(self.preferences.path))
    def set_overlay_lock(self,key,value):
        self.settings[key]=value
        if not value:self.settings['click_through']=False
        self.preferences.save();self.apply_overlay_settings()
    def set_all_locks(self,value):
        self.settings['dps_locked']=value;self.settings['graph_locked']=value
        self.settings['event_locked']=value
        if not value:self.settings['click_through']=False
        self.preferences.save();self.apply_overlay_settings()
    def apply_overlay_settings(self):
        from .appearance import appearance
        theme=appearance(self.settings,'dps');family=theme['font_family'].replace('"','').replace('\\','')
        accent=self.settings['accent']
        self.setStyleSheet(f'''QMainWindow,QWidget {{background:{theme['background']};color:{theme['text']};font:{theme['font_size']}pt "{family}";}}
            QLabel#title {{font-weight:700;font-size:{theme['font_size']+12}pt;color:{accent};}}
            QLabel#muted {{color:{theme['secondary']};}}
            QLabel#badge {{color:{accent};background:{theme['header']};border:1px solid {accent};border-radius:8px;padding:6px 10px;font-weight:700;}}
            QLabel#summary {{padding:16px;background:{theme['header']};border-radius:8px;}}
            QLabel#notice {{color:{accent};}}
            QPushButton,QComboBox {{background:{theme['controls']};color:{theme['control_text']};padding:8px 12px;border:1px solid {theme['secondary']};border-radius:5px;}}
            QPushButton:hover {{border-color:{accent};}}
            QPushButton:checked,QPushButton#primaryAction {{border:2px solid {accent};}}
            QCheckBox {{spacing:8px;}}
            QTabWidget::pane {{border:1px solid {theme['controls']};border-radius:6px;}}
            QTabBar::tab {{padding:9px 20px;background:{theme['background']};color:{theme['secondary']};border-bottom:2px solid transparent;}}
            QTabBar::tab:selected {{color:{accent};border-bottom:2px solid {accent};background:{theme['header']};}}
            QGroupBox {{border:1px solid {theme['controls']};border-radius:7px;margin-top:10px;padding:16px 12px 12px;font-weight:600;}}
            QGroupBox::title {{subcontrol-origin:margin;left:12px;padding:0 6px;color:{theme['text']};}}
            QScrollArea {{border:0;}}''')
        self.storage_status.setStyleSheet(f"color:{theme['secondary']};font-size:{max(8,theme['font_size']-1)}pt;")

        mode=self.settings.get('attachment_mode','Frei schwebend')
        self.overlay.configure({**self.settings,'attached':mode in ('Beide an AION 2','Nur DPS an AION 2')},self.settings['overlay'])
        self.graph_overlay.configure({**self.settings,'opacity':self.settings.get('graph_opacity',self.settings['opacity']),'attached':mode in ('Beide an AION 2','Nur Graph an AION 2')},self.settings['graph_overlay'])
        from .language import text,get_language
        self.event_overlay.configure_events({**self.settings,'language':get_language()})
        self.event_toggle.setText(text(get_language(),'Event clock','Event-Uhr'))
        self.event_options.setText(text(get_language(),'Customize','Anpassen'))
        locked=self.settings.get('dps_locked',False) and self.settings.get('graph_locked',False)
        self.lock_toggle.blockSignals(True);self.lock_toggle.setChecked(locked);self.lock_toggle.setText(_tr('Lösen') if locked else _tr('Fixieren'));self.lock_toggle.blockSignals(False)
        for view in (self.view,self.overlay.view,self.graph_overlay.view):view.set_data(self.display_report(),self.settings)
    def save_overlay_position(self,key,position):
        self.settings[key]=position;self.preferences.save()
    def change_option(self,key,value):
        self.settings[key]=value;self.preferences.save();self.apply_overlay_settings()
    def configure_events(self):self.configure('clock')
    def hide_event_overlay(self):
        self.event_toggle.setChecked(False)
    def disable_overlay(self,key):
        widget=self.overlay_toggle if key=='overlay' else self.graph_toggle
        widget.setChecked(False)
    def configure(self,section='global',page='settings'):
        dialog=SettingsDialog(self.settings,self.data_dir,self);dialog.select_section(section,page)
        if dialog.exec()==QDialog.DialogCode.Accepted:
            self.settings.update(dialog.result_settings());self.preferences.save()
            diagnostics.set_enabled(self.settings['save_debug'],self.data_dir)
            for widget,key in [(self.overlay_toggle,'overlay'),(self.graph_toggle,'graph_overlay'),(self.event_toggle,'event_overlay')]:
                widget.blockSignals(True);widget.setChecked(self.settings[key]);widget.blockSignals(False)
            self.attach_toggle.blockSignals(True);self.attach_toggle.setCurrentIndex(max(0,self.attach_toggle.findData(self.settings['attachment_mode'])));self.attach_toggle.blockSignals(False)
            self.skill_labels=SkillLabels.for_runtime(self.data_dir,self.settings)
            for pane in self.details:pane.skill_labels=self.skill_labels
            self.apply_overlay_settings()
            self.log_writer=CombatLogWriter(self.combat_directory())
            if self.worker and self.worker.isRunning():
                self.worker.set_recording(self.settings['save_packets']);self.worker.set_logging(self.settings['save_combat'],self.combat_directory())
                with self.worker.session.lock:
                    self.worker.session.core.skill_labels=self.skill_labels
                    ledger=self.worker.session.core.ledger
                    if ledger.track_pvp!=self.settings['track_pvp']:ledger.finish('settings_change')
                    ledger.track_pvp=self.settings['track_pvp']
                self.worker.emit_snapshot(True)
            self.update_storage_status()
    def start_live(self):
        if self.closing or (self.worker and self.worker.isRunning()):return
        self.latest={'fights':[]};self.display_floor=0;self.render()
        self.worker=MeterWorker('live','auto',record=self.settings['save_packets'],data_dir=self.data_dir)
        worker=self.worker;self.workers=[w for w in self.workers if w.isRunning()];self.workers.append(worker)
        worker.status.connect(lambda text,w=worker:self.worker_status(w,text))
        worker.failed.connect(lambda text,w=worker:self.failure(w,text))
        worker.finished.connect(lambda w=worker:self.completed(w))
        self.capture_button.setText(_tr('Live pausieren'));self.live_badge.setText('LIVE');worker.start()
    def worker_status(self,worker,text):
        if worker is self.worker:self.status.setText(_tr('Warte auf AION 2 …') if 'TCP 13328' in text else text)
    def failure(self,worker,text):
        if worker is self.worker:self.status.setText(_tr('Aufnahme nicht verfügbar: Npcap prüfen. ')+text)
    def toggle_capture(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel.set();self.capture_button.setEnabled(False)
        else:self.start_live()
    def poll(self):
        if self.worker and self.worker.last_report is not None and self.worker.last_report is not self.latest:
            self.latest=self.worker.last_report;self.render();self.save_finished()
    def render(self):
        self.scope_controls.setVisible(bool(self.latest.get('fights') and self.latest['fights'][-1].get('dungeon_name')))
        if self.latest.get('session',{}).get('mode') not in (None,'live'):
            raise ValueError(_tr('Die Live-Ansicht übernimmt keine Replay-Daten.'))
        own=self.latest.get('self_identity',{})
        if own.get('confirmed') and own.get('source')=='server' and own.get('name') and own.get('server'):
            profile={'name':own['name'],'server':own['server']}
            if self.settings.get('character_identity')!=profile:
                self.settings['character_identity']=profile;self.settings['character_name']=own['name'];self.preferences.save()
        state=self.latest.get('group_state','missing');name=own.get('name','') if own.get('confirmed') else ''
        prefix=(name+' · ') if name else ''
        messages={'missing':_tr('Warte auf eine frische Gruppenmeldung · ggf. Gebiet wechseln oder bei laufendem Meter neu beitreten.'), 'invalid':_tr('Gruppendaten unvollständig · Mitglieder werden noch nicht gezählt.'), 'partial':_tr('{0} Mitglieder erkannt · Vollständigkeit der Gruppen-/Raidliste unbestätigt.' ,len(self.latest.get('roster', []))), 'solo':_tr('Keine Gruppe gemeldet.')}
        self.group_status.setText(prefix+messages.get(state,_tr('Gruppen-/Raidliste: {0} Mitglieder' ,len(self.latest.get('roster', [])))))
        self.identity_button.setVisible(self.settings.get('manual_identity',False) and self.latest.get('self_id') is None)
        from .metrics import metric_report,METRICS
        mode=self.settings.get('display_metric','damage');unit=METRICS[mode];rate='DPS' if mode=='damage' else 'HPS'
        fights=metric_report(self.display_report(),mode).get('fights',[]);fight=fights[-1] if fights else None
        if fight:
            seconds=int(fight['seconds']);total=fight.get('total_damage')
            dps=total/fight['seconds'] if total is not None else None
            self.summary.setText(f"<b style='font-size:{max(18,self.settings.get('dps_font_size',14)+4)}pt'>{number(dps)} Ø {rate}</b> &nbsp;·&nbsp; {number(total)} {unit} &nbsp;·&nbsp; {seconds//60}:{seconds%60:02}")
            self.notice.setText(_tr('Nur ein Teilausschnitt erfasst.') if fight.get('partial') else '')
            if fight.get('integrity','ok')!='ok':self.notice.setText(_tr('Paketkonflikt: Diese DPS-Auswertung ist nicht verlässlich.'))
            if self.worker and self.worker.isRunning():self.status.setText(fight.get('boss_name') or (_tr('Kampf läuft') if fight['reason']=='active' else _tr('Kampf beendet · bereit für den nächsten')))
        else:
            self.summary.setText(f"<b style='font-size:18pt'>0 Ø {rate}</b> &nbsp;·&nbsp; 0 {unit} &nbsp;·&nbsp; 0:00")
            self.notice.setText(_tr('Charakter wird automatisch aus Spielmeldungen erkannt …') if self.latest.get('self_id') is None else _tr('Nur du und deine Gruppe.'))
        if self.latest.get('self_id') is not None and not own.get('name') and (not fight or (not fight.get('partial') and fight.get('integrity','ok')=='ok')):
            self.notice.setText(_tr('Eigener Spieler erkannt – warte auf die Namensmeldung.'))
        if self.latest.get('coverage_incomplete') and (not fight or fight.get('integrity','ok')=='ok'):
            self.notice.setText(_tr('Auswertung noch unvollständig: nicht alle Effekte/Begleiter sind zugeordnet.'))
        if fight and fight.get('integrity','ok')=='ok' and fight.get('damage_coverage')=='sparse_worldboss_amounts':
            self.notice.setText(_tr('Worldboss: Schadensbeträge vieler Spieler fehlen offenbar. Raid-DPS/Anteile sind unvollständig.'))
        elif fight and fight.get('boss_type')=='world_boss' and fight.get('integrity','ok')=='ok':self.notice.setText(_tr('Worldboss: nur erfasste Gruppe/Raid · keine Gesamtwertung aller Angreifer.'))
        if mode!='damage' and (not fight or fight.get('integrity','ok')=='ok'):self.notice.setText(_tr('Beobachtete Heilung im erfassten Kampf · keine bestätigte effektive Heilung/Überheilung.')+(_tr(' Teilausschnitt.') if fight and fight.get('partial') else '')+(_tr(' Ältere Logs enthalten keine sichere Selbst-/Fremdaufteilung.') if fight and fight.get('healing_legacy') else ''))
        for view in (self.view,self.overlay.view,self.graph_overlay.view):view.set_data(self.display_report(),self.settings)
        if fight and fight.get('scope_note'):self.notice.setText(fight['scope_note'])
        for dialog in list(self.details):dialog.set_report(self.display_report() if self.settings.get('dungeon_scope','all')!='all' else self.latest)
        self.update_storage_status()
    def completed(self,worker):
        if worker is not self.worker:return
        if worker.last_report:self.latest=worker.last_report;self.render();self.save_finished(True)
        self.capture_button.setEnabled(True);self.capture_button.setText(_tr('Live fortsetzen'));self.live_badge.setText(_tr('PAUSIERT'))
    def save_finished(self,force=False):
        if not self.settings['save_combat']:return
        if self.worker:
            # The capture worker persists snapshots even with a hidden or busy UI.
            if force:self.worker.emit_snapshot(True)
            return
        try:
            if self.log_writer.directory!=self.combat_directory():self.log_writer=CombatLogWriter(self.combat_directory())
            self.log_writer.save(self.latest,force)
        except (OSError,ValueError) as error:self.notice.setText(_tr('Log konnte nicht gespeichert werden: ')+str(error))
    def choose_self(self):
        candidates=self.latest.get('identity_candidates',[])
        if not candidates:
            self.notice.setText(_tr('Noch keine Spieler erkannt. Meter vor Login/Zonenwechsel starten.'));return
        labels=[f"{item['name'] or _tr('Unbekannter Spieler')} · {item['class'] or '?'} · Entity {item['id']}" for item in candidates]
        label,ok=QInputDialog.getItem(self,_tr('Eigener Charakter'),_tr('Deine bestätigte Entity auswählen:'),labels,0,False)
        if ok:self.name_actor(candidates[labels.index(label)]['id'])
    def name_actor(self,actor):
        if not self.worker or not self.settings.get('manual_identity',False):return
        default=self.settings.get('character_name','')
        name,ok=QInputDialog.getText(self,_tr('Eigener Spieler'),_tr('Ist Spieler {0} dein Charakter? Eigenen Namen eingeben:' ,actor),text=default)
        if not ok:return
        try:
            self.worker.session.manual_self_name(actor,name.strip());self.worker.emit_snapshot(True)
            self.latest=self.worker.last_report;self.settings['character_name']=name.strip();self.preferences.save();self.render()
        except ValueError as exc:self.notice.setText(str(exc))
    def closeEvent(self,event):
        self.settings['window_size']=[self.width(),self.height()];self.settings['window_position']=[self.x(),self.y()]
        for prefix,overlay in [('dps',self.overlay),('graph',self.graph_overlay),('event',self.event_overlay)]:
            overlay.commit_size()
            self.settings[prefix+'_size']=[overlay.width(),overlay.height()]
            if not overlay.attached:self.settings[prefix+'_free_position']=[overlay.x(),overlay.y()]
        self.preferences.save()
        running=[w for w in self.workers if w.isRunning()]
        if running:
            self.closing=True
            for worker in running:worker.cancel.set()
            event.ignore();QTimer.singleShot(100,self.finish_close);return
        self.save_finished(True)
        for dialog in list(self.history_dialogs)+list(self.details):dialog.close()
        for overlay in (self.overlay,self.graph_overlay,self.event_overlay):overlay.wanted=False;overlay.hide();overlay.timer.stop();overlay.geometry_timer.stop()
        self.event_overlay.tick.stop()
        self.timer.stop();event.accept()
    def finish_close(self):
        if any(w.isRunning() for w in self.workers):QTimer.singleShot(100,self.finish_close);return
        self.poll();self.close()
