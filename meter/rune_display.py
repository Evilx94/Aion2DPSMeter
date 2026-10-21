"""Compact rune labels with explicit evidence status; damage accounting is unchanged."""
from .language import tr

# Class-level live confirmation reported by the user on 2026-10-21.
# This confirms the displayed rune pattern, not every effect or raw ID.
USER_CONFIRMED_RUNE_FAMILIES={15,17,18}


def rune_display(row):
    slots=row.get('specialization_slots');status=row.get('specialization_status')
    if slots is None or not status:
        return '—',tr('Für diese ID werden keine Runen angezeigt.'),'unknown'
    value=' + '.join(str(slot) for slot in slots) if slots else tr('Keine Runen')
    if status=='confirmed_exact':
        return value,tr('Runenauswahl für diese exakte Bolt-ID im eigenen zeitlich zugeordneten Versuch bestätigt.'),status
    if status in ('pattern_candidate','derived_charge_variant') and row.get('skill',0)//1_000_000 in USER_CONFIRMED_RUNE_FAMILIES:
        return value,tr('Runendarstellung für diese Klasse im Spiel vom Nutzer bestätigt.'),'user_confirmed_pattern'
    if status=='derived_charge_variant':
        return value+' *',tr('Aus dem bestätigten Bolt-Runenblock abgeleitet; diese Rohvariante wurde nicht separat auf ihre Runenauswahl getestet.'),status
    return value+' *',tr('Aus dem Zahlenmuster der bekannten Skillfamilie abgeleitet. Runenauswahl dieser Variante nicht unabhängig bestätigt; keine Aussage über den ausgelösten Untereffekt.'),status
