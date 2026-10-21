"""Qt timezone support; no separate Python timezone database is required."""
from PySide6.QtCore import QTimeZone,Qt
from PySide6.QtWidgets import QComboBox

DEFAULT_ZONE='Europe/Berlin'

def timezone(value):
    if value=='system':return QTimeZone.systemTimeZone()
    if not isinstance(value,str) or not 0<len(value)<=128:return QTimeZone()
    return QTimeZone(value.encode('utf-8'))

def valid_zone(value):return timezone(value).isValid()

def zone_id(value):
    zone=timezone(value)
    if not zone.isValid():return DEFAULT_ZONE
    return bytes(zone.id()).decode('utf-8')

def zone_picker(value,language='en'):
    box=QComboBox();box.setEditable(True);box.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
    box.addItem('System time zone' if language=='en' else 'Systemzeitzone','system')
    ids=sorted({bytes(v).decode('utf-8') for v in QTimeZone.availableTimeZoneIds()}|{'UTC'})
    for key in ids:box.addItem(key,key)
    at=box.findData(value)
    if at>=0:box.setCurrentIndex(at)
    else:box.setEditText(value)
    box.completer().setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
    box.completer().setFilterMode(Qt.MatchFlag.MatchContains)
    box.setMinimumContentsLength(18);box.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
    return box

def selected_zone(box):
    i=box.currentIndex()
    return box.itemData(i) if i>=0 and box.currentText()==box.itemText(i) else box.currentText().strip()
