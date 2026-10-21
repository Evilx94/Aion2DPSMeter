"""Manual pet checklist; independent of combat capture and entity ownership."""
import json
from pathlib import Path
from PySide6.QtCore import Qt,QEvent,QPoint,QSize
from PySide6.QtGui import QPainter,QColor,QPen,QPolygon
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QComboBox,
    QCheckBox,QTableWidget,QTableWidgetItem,QHeaderView,QDialogButtonBox,
    QStyledItemDelegate,QStyleOptionViewItem,QStyle,QApplication)
from .language import text,get_language


def catalog():
    return json.loads((Path(__file__).parent/'data/pets.json').read_text(encoding='utf-8'))['pets']


class OwnershipDelegate(QStyledItemDelegate):
    """Visible centered checkbox retaining Qt check-state and keyboard semantics."""
    def paint(self,painter,option,index):
        clean=QStyleOptionViewItem(option);self.initStyleOption(clean,index)
        clean.features &= ~QStyleOptionViewItem.ViewItemFeature.HasCheckIndicator
        (option.widget.style() if option.widget else QApplication.style()).drawControl(QStyle.ControlElement.CE_ItemViewItem,clean,painter,option.widget)
        checked=index.data(Qt.ItemDataRole.CheckStateRole)==Qt.CheckState.Checked.value
        box=option.rect.adjusted(0,0,0,0);box.setSize(QSize(22,22));box.moveCenter(option.rect.center())
        painter.save();painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor('#71ddc4') if checked else QColor('#a4bbc8'),2))
        painter.setBrush(QColor('#71ddc4') if checked else QColor('#243b49'));painter.drawRoundedRect(box.adjusted(1,1,-1,-1),4,4)
        if checked:
            painter.setPen(QPen(QColor('#10252b'),2.5,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap,Qt.PenJoinStyle.RoundJoin))
            painter.drawPolyline(QPolygon([QPoint(box.left()+5,box.top()+11),QPoint(box.left()+9,box.top()+15),QPoint(box.left()+17,box.top()+6)]))
        painter.restore()
    def editorEvent(self,event,model,option,index):
        if event.type()==QEvent.Type.MouseButtonRelease and event.button()==Qt.MouseButton.LeftButton:
            pass
        elif event.type()==QEvent.Type.KeyPress and event.key() in (Qt.Key.Key_Space,Qt.Key.Key_Select):
            pass
        else:return False
        if not index.flags() & Qt.ItemFlag.ItemIsEnabled:return False
        checked=index.data(Qt.ItemDataRole.CheckStateRole)==Qt.CheckState.Checked.value
        return model.setData(index,Qt.CheckState.Unchecked if checked else Qt.CheckState.Checked,Qt.ItemDataRole.CheckStateRole)


class PetChecklist(QDialog):
    def __init__(self,preferences,parent=None):
        super().__init__(parent);self.preferences=preferences;self.rows=catalog();self.language=get_language();t=self.t
        self.setWindowTitle(t('Pet checklist','Pet-Checkliste'));self.resize(800,580)
        layout=QVBoxLayout(self)
        hint=QLabel(t('Manual checklist · saved locally','Manuelle Checkliste · lokal gespeichert'));hint.setWordWrap(True);layout.addWidget(hint)
        controls=QHBoxLayout();self.search=QLineEdit();self.search.setPlaceholderText(t('Search pet, family or source…','Pet, Familie oder Quelle suchen…'));controls.addWidget(self.search,1)
        self.category=QComboBox()
        for key,en,de in [('all','All pets','Alle Pets'),('dungeon','Dungeon pets','Dungeon-Pets'),('candidate','Shop / chests','Shop / Kisten'),('special','Special pets','Special-Pets')]:self.category.addItem(t(en,de),key)
        controls.addWidget(self.category);layout.addLayout(controls)
        self.hide_owned=QCheckBox(t('Hide collected','Gesammelte ausblenden'));layout.addWidget(self.hide_owned)
        self.progress=QLabel();layout.addWidget(self.progress)
        self.table=QTableWidget(0,4);self.table.setHorizontalHeaderLabels([t('Owned','Besitz'),'Pet',t('Family','Familie'),t('Location / source','Ort / Quelle')]);layout.addWidget(self.table,1)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows);self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        header=self.table.horizontalHeader();header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        for column in (0,2):header.setSectionResizeMode(column,QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0,76);self.table.setColumnWidth(2,90)
        for column in (1,3):header.setSectionResizeMode(column,QHeaderView.ResizeMode.Stretch)
        self.table.setItemDelegateForColumn(0,OwnershipDelegate(self.table))
        self.table.setAlternatingRowColors(True);self.table.setShowGrid(False);self.table.setWordWrap(True)
        self.table.setStyleSheet('QTableWidget{background:#152630;alternate-background-color:#1c303d;border:1px solid #36515f;selection-background-color:#345568;selection-color:#f1f7fa;} QTableWidget::item{padding:7px;} QHeaderView::section{background:#243b49;color:#dce9f2;border:0;border-bottom:1px solid #456170;padding:9px;font-weight:600;}')
        self.table.verticalHeader().setMinimumSectionSize(48);self.table.verticalHeader().hide()
        self.error=QLabel();self.error.setWordWrap(True);self.error.setStyleSheet('color:#ffab91');layout.addWidget(self.error)
        hint_sources=QLabel(t('Dungeon, shop / chest and special pets','Dungeon-, Shop-/Kisten- und Special-Pets'));layout.addWidget(hint_sources)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Close);buttons.rejected.connect(self.close);layout.addWidget(buttons)
        self.search.textChanged.connect(self.render);self.category.currentIndexChanged.connect(self.render);self.hide_owned.toggled.connect(self.render);self.table.itemChanged.connect(self.changed)
        self.render()
    def t(self,en,de):return text(self.language,en,de)
    def source_text(self,row):
        if row['category']=='dungeon':
            return row['location']+'\n'+(row['note'] or row['name'])
        return row['location'] or self.t('Source unknown','Quelle ungeklärt')
    def render(self,*args):
        saved=set(self.preferences.values['pets_owned']);owned={r['id'] for r in self.rows if saved & {r['id'],*r.get('ownership_aliases',[])}};query=self.search.text().strip().casefold();category=self.category.currentData()
        visible=[r for r in self.rows if (category=='all' or r['category']==category) and (not self.hide_owned.isChecked() or r['id'] not in owned) and query in ' '.join((r['name'],r['family'],self.source_text(r))).casefold()]
        self.table.blockSignals(True)
        try:
            self.table.setRowCount(len(visible))
            for i,row in enumerate(visible):
                check=QTableWidgetItem();check.setFlags(Qt.ItemFlag.ItemIsEnabled|Qt.ItemFlag.ItemIsUserCheckable|Qt.ItemFlag.ItemIsSelectable);check.setData(Qt.ItemDataRole.UserRole,row['id']);check.setCheckState(Qt.CheckState.Checked if row['id'] in owned else Qt.CheckState.Unchecked);self.table.setItem(i,0,check)
                for col,value in enumerate((row['name'],row['family'] or '—',self.source_text(row)),1):
                    item=QTableWidgetItem(value);item.setTextAlignment(Qt.AlignmentFlag.AlignCenter);item.setToolTip(value);self.table.setItem(i,col,item)
            self.table.resizeRowsToContents()
        finally:self.table.blockSignals(False)
        selected=[r for r in self.rows if category=='all' or r['category']==category];count=sum(r['id'] in owned for r in selected)
        self.progress.setText(self.t('{0} / {1} collected · {2} shown','{0} / {1} gesammelt · {2} angezeigt').format(count,len(selected),len(visible)))
    def changed(self,item):
        if item.column()!=0:return
        old=list(self.preferences.values['pets_owned']);owned=set(old);key=item.data(Qt.ItemDataRole.UserRole)
        row=next(r for r in self.rows if r['id']==key)
        owned.difference_update(row.get('ownership_aliases',[]))
        if item.checkState()==Qt.CheckState.Checked:owned.add(key)
        else:owned.discard(key)
        self.preferences.values['pets_owned']=sorted(owned)
        try:self.preferences.save()
        except OSError as exc:
            self.preferences.values['pets_owned']=old;self.error.setText(self.t('Could not save checklist: ','Checkliste konnte nicht gespeichert werden: ')+str(exc))
        else:self.error.clear()
        self.render()
