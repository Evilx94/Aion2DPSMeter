"""Presentation of captured roster gear/combat power; missing is not zero."""
from .language import tr as _tr
def metric(value):return str(value) if type(value) is int and value>0 else '—'

def equipment_text(actor,show_missing=True):
    if not show_missing and metric(actor.get('gear'))=='—' and metric(actor.get('power'))=='—':return ''
    return _tr('GS ')+metric(actor.get('gear'))+' · Combat Score '+metric(actor.get('power'))
