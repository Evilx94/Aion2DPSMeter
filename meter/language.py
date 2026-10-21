"""Explicit UI language selection; game names and stored identifiers stay stable."""
import json
from pathlib import Path

_LANGUAGE='en'
_QT_TRANSLATOR=None
_ENGLISH=json.loads((Path(__file__).parent/'data'/'ui_en.json').read_text(encoding='utf-8')) if (Path(__file__).parent/'data'/'ui_en.json').exists() else {}

def set_language(language):
    global _LANGUAGE
    _LANGUAGE=language if language in ('en','de') else 'en'
    _install_qt_language()

def get_language():return _LANGUAGE

def tr(source,*args):
    """Translate authored UI templates, never external names or stored IDs."""
    value=source if _LANGUAGE=='de' else _ENGLISH.get(source,source)
    return value.format(*args) if args else value

def decimal(value):
    return value.replace('.',',') if _LANGUAGE=='de' else value

def _install_qt_language():
    from PySide6.QtCore import QCoreApplication,QLocale,QTranslator,QLibraryInfo
    global _QT_TRANSLATOR
    app=QCoreApplication.instance()
    if app is None:return
    QLocale.setDefault(QLocale('de_DE' if _LANGUAGE=='de' else 'en_GB'))
    if _QT_TRANSLATOR is None:
        _QT_TRANSLATOR=QTranslator(app)
        _QT_TRANSLATOR.load('qtbase_de',QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath))
    app.removeTranslator(_QT_TRANSLATOR)
    if _LANGUAGE=='de':app.installTranslator(_QT_TRANSLATOR)

class TranslatedDict(dict):
    """Labels are resolved at access time; dictionary keys stay machine-readable."""
    def __getitem__(self,key):return tr(super().__getitem__(key))
    def get(self,key,default=None):return self[key] if key in self else default
    def items(self):return ((key,self[key]) for key in self)
    def values(self):return (self[key] for key in self)
def text(language,en,de):
    return de if language=='de' else en

EVENT_NAMES={
    'rift':('Rift · Portaleintritt','Spacetime Rift'),
    'invasion':('Dimensionsinvasion','Dimensional Invasion'),
    'siege':('Artefaktbelagerung','Artifact Siege'),
    'arena_day':('Arena of Tactics · tagsüber','Arena of Tactics · Daytime'),
    'arena_evening':('Arena of Tactics · abends','Arena of Tactics · Evening'),
}

def migrate_event_names(rows):
    from copy import deepcopy
    result=deepcopy(rows)
    for row in result:
        old,new=EVENT_NAMES.get(row.get('id'),(None,None))
        if old and row.get('name')==old and row.get('status')!='user' and row.get('source')!='user':
            row['name']=new
    return result
