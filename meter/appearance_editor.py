"""Reusable visual controls with previews and independent per-overlay styles."""
from copy import deepcopy
from PySide6.QtCore import Qt,Signal
from PySide6.QtGui import QColor,QFont
from PySide6.QtWidgets import QWidget,QVBoxLayout,QFormLayout,QHBoxLayout,QPushButton,QColorDialog,QLabel,QFontComboBox,QSpinBox,QSlider,QTabWidget,QComboBox,QStackedWidget,QSizePolicy
from .appearance import THEMES,LABELS,appearance,clean_appearance,contrast_ratio
from .language import text

class AppearanceEditor(QWidget):
    changed=Signal()
    def __init__(self,settings,sections=('dps','graph'),language='en',parent=None):
        super().__init__(parent);self.settings=deepcopy(settings);self.language=language
        self.values=clean_appearance(settings.get('appearance',{}));self.controls={};self.previews={};self.pages={};self.forms={}
        outer=QVBoxLayout(self);outer.setContentsMargins(0,0,0,0)
        tabs=QTabWidget();self.tabs=tabs;outer.addWidget(tabs)
        names={'dps':('DPS / healing','DPS / Heilung'),'graph':('Graph','Graph'),'clock':('Clock appearance','Uhr-Darstellung')}
        for section in sections:
            self.values[section]=appearance(settings,section);page=QWidget();page_layout=QVBoxLayout(page);page_layout.setContentsMargins(0,0,0,0);fields=QWidget();form=QFormLayout(fields);page_layout.addWidget(fields,0,Qt.AlignmentFlag.AlignTop);page_layout.addStretch(1);tabs.addTab(page,self.t(*names[section]));self.pages[section]=page;self.forms[section]=form;controls={};self.controls[section]=controls
            preset=QComboBox();preset.addItem(self.t('Custom / current','Eigene / aktuell'),'custom');preset.addItem(self.t('Default','Standard'),'default');preset.addItem(self.t('High contrast','Hoher Kontrast'),'contrast');form.addRow(self.t('Preset','Vorlage'),preset)
            preset.currentIndexChanged.connect(lambda i,s=section,b=preset:self.apply_preset(s,b.currentData()))
            family=QFontComboBox();family.setMinimumContentsLength(12);family.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon);family.setCurrentFont(QFont(self.values[section]['font_family']));form.addRow(self.t('Font','Schriftart'),family);controls['font_family']=family
            family.currentFontChanged.connect(lambda font,s=section:self.set_value(s,'font_family',font.family()))
            size=QSpinBox();size.setRange(8,24);size.setSuffix(' pt');size.setValue(self.values[section]['font_size']);form.addRow(self.t('Text size','Schriftgröße'),size);controls['font_size']=size;size.valueChanged.connect(lambda v,s=section:self.set_value(s,'font_size',v))
            all_text=QPushButton();controls['all_text']=all_text;self.style_button(all_text,self.values[section]['text']);all_text.setAccessibleName(self.t('All text colors','Alle Textfarben'))
            all_text.clicked.connect(lambda checked=False,s=section:self.choose_all_text(s));form.addRow(self.t('Text color (all)','Textfarbe (alle)'),all_text)
            color_row=QHBoxLayout();roles=QComboBox();roles.setMinimumContentsLength(8);roles.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon);roles.setAccessibleName(self.t('Other color elements','Andere Farbelemente'));stack=QStackedWidget();stack.setFixedHeight(32);color_row.addWidget(roles,1);color_row.addWidget(stack)
            form.addRow(self.t('Other colors','Weitere Farben'),color_row);roles.currentIndexChanged.connect(stack.setCurrentIndex)
            direct={'text','secondary','control_text','bar_text','bar_detail','event_text','countdown','accent'}
            for key in LABELS:
                if key not in THEMES[section]:continue
                button=QPushButton();controls[key]=button;self.style_button(button,self.values[section][key]);label=self.t(*LABELS[key]);button.setAccessibleName(label);button.setToolTip(self.t('Choose a color or enter a hex value in the color dialog.','Farbe wählen oder im Farbdialog einen Hexwert eingeben.'))
                button.clicked.connect(lambda checked=False,s=section,k=key:self.choose_color(s,k))
                if key in direct:form.addRow(label,button)
                else:stack.addWidget(button);roles.addItem(label,key)
            if section=='dps':
                opacity=QSlider(Qt.Orientation.Horizontal);opacity.setRange(10,100);opacity.setValue(self.values[section]['bar_opacity']);controls['bar_opacity']=opacity;form.addRow(self.t('Bar fill strength','Balkendeckkraft'),opacity);opacity.valueChanged.connect(lambda v,s=section:self.set_value(s,'bar_opacity',v))
            label=QLabel();label.setWordWrap(True);label.setSizePolicy(QSizePolicy.Policy.Preferred,QSizePolicy.Policy.Maximum);controls['contrast']=label;form.addRow(label)
            if section=='clock':
                from .event_overlay import EventView
                preview=EventView();preview.resize(380,140)
            else:
                from .overlay import DamageView
                preview=DamageView(section=='graph');preview.setMinimumHeight(210)
            self.previews[section]=preview;form.addRow(preview);self.refresh_preview(section)
    def t(self,en,de):return text(self.language,en,de)
    @staticmethod
    def style_button(button,color):
        foreground='#000000' if contrast_ratio('#000000',color)>=contrast_ratio('#ffffff',color) else '#ffffff'
        button.setText(color.upper());button.setStyleSheet(f'background:{color};color:{foreground};border:1px solid #7895a2;padding:4px;')
    def set_value(self,section,key,value):
        self.values[section][key]=value
        if key in LABELS:self.style_button(self.controls[section][key],value)
        if key=='text':self.style_button(self.controls[section]['all_text'],value)
        if section in self.previews:self.refresh_preview(section)
        self.changed.emit()
    def set_text_color(self,section,color):
        for key in ('text','secondary','control_text','bar_text','bar_detail','event_text','countdown'):
            if key in self.values[section]:self.set_value(section,key,color)
    def choose_all_text(self,section):
        color=QColorDialog.getColor(QColor(self.values[section]['text']),self,self.t('All text colors','Alle Textfarben'))
        if color.isValid():self.set_text_color(section,color.name())
    def choose_color(self,section,key):
        color=QColorDialog.getColor(QColor(self.values[section][key]),self,self.t(*LABELS[key]))
        if color.isValid():self.set_value(section,key,color.name())
    def apply_preset(self,section,preset):
        if preset=='custom':return
        values=deepcopy(THEMES[section])
        if preset=='contrast':
            for key in values:
                if key in LABELS:values[key]='#000000' if key in ('background','header','controls','track') else '#ffffff'
            if 'grid' in values:values['grid']='#808080'
        self.values[section]=values
        for key,control in self.controls[section].items():
            control.blockSignals(True)
            if key=='all_text':self.style_button(control,values['text'])
            elif key in LABELS:self.style_button(control,values[key])
            elif key=='font_family':control.setCurrentFont(QFont(values[key]))
            elif key in ('font_size','bar_opacity'):control.setValue(values[key])
            control.blockSignals(False)
        self.refresh_preview(section);self.changed.emit()
    def refresh_preview(self,section):
        settings={**self.settings,'appearance':self.result(),'language':self.language}
        view=self.previews[section]
        if section=='clock':view.settings=settings;view.refresh()
        else:
            fight={'seconds':20,'total_damage':30000,'target_name':self.t('Example target','Beispielgegner'),'integrity':'ok','actors':[{'id':1,'name':'Player 1','class':'Sorcerer','damage':20000,'dps':1000},{'id':2,'name':'Player 2','class':'Cleric','damage':10000,'dps':500}], 'timeline':[{'second':i,'damage':1000+(i%5)*250} for i in range(20)]}
            view.set_data({'fights':[fight],'self_id':1,'group_state':'members'},settings)
            view.setMinimumHeight(round(210*self.values[section]['font_size']/10))
        view.setFixedHeight(view.minimumHeight())
        colors=self.values[section];text_keys=('text','event_text','countdown') if section=='clock' else ('text','secondary')
        ratios=[contrast_ratio(colors[k],colors['background']) for k in text_keys]
        ratios.extend((contrast_ratio(colors['control_text'],colors['controls']),contrast_ratio(colors['text'],colors['header'])))
        if section=='dps':
            from .overlay import CLASS_COLORS,color_for
            alpha=colors['bar_opacity']/100
            for index,cls in enumerate(CLASS_COLORS):
                shade=color_for({'class':cls},index,settings)
                blended='#'+''.join(f"{round(int(shade[i:i+2],16)*alpha+int(colors['background'][i:i+2],16)*(1-alpha)):02x}" for i in (1,3,5))
                ratios.extend(contrast_ratio(colors[key],blended) for key in ('bar_text','bar_detail'))
        ratio=min(ratios)
        self.controls[section]['contrast'].setText(self.t('Text contrast','Textkontrast')+f': {ratio:.1f}:1'+self.t(' · choose at least 4.5:1 for small text.',' · für kleine Schrift mindestens 4,5:1 wählen.'))
    def result(self):return deepcopy(self.values)
