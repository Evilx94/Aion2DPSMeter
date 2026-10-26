"""Evidence labels describe observations, never certify complete player capture."""
from .language import tr as _tr
from .language import TranslatedDict
LABELS=TranslatedDict({'conflict':'Nicht verlässlich','partial':'Eingeschränkt','observed':'Werte beobachtet','activity_only':'Nur Casts / Trigger','unknown':'Keine Mengenbelege'})

def player_quality(actor,fight):
    stored=actor.get('data_quality',{})
    if not isinstance(stored,dict):stored={}
    damage=stored.get('damage_events');heals=stored.get('healing_events');casts=stored.get('casts',actor.get('casts'))
    notices=stored.get('hit_notices',actor.get('hit_notices',0))
    raw_issues=stored.get('issues',{});issues=dict(raw_issues) if isinstance(raw_issues,dict) else {};notes=[]
    if fight.get('integrity','ok')!='ok':status='conflict';notes.append(_tr('Paketkonflikt oder ungültige Kampfdaten'))
    elif issues:status='partial'
    elif (actor.get('damage') or 0)>0 or (actor.get('healing') or 0)>0:status='observed'
    elif casts or notices:status='activity_only';notes.append(_tr('Auslösungen ohne verwertbare Schadens-/Heilungsmenge'))
    else:status='unknown'
    from .observation_quality import damage_amount_missing,damage_amount_partial
    if damage_amount_missing(actor,fight):notes.append(_tr('Kein Schadensbetrag erfasst; 0 Schaden ist nicht bestätigt.'))
    if damage_amount_partial(actor,fight):
        if status!='conflict':status='partial'
        notes.append(_tr('Nur periodische Schadensbeträge erfasst; direkte Treffer fehlen.'))
    if notices and not fight.get('metric'):
        notes.append(_tr('{0} Treffermeldungen ohne Schadensfeld; getrennt von Schadenssummen.',notices))
    if issues:notes.extend(f'{key}: {value}' for key,value in sorted(issues.items()))
    if not stored:notes.append(_tr('Älterer Log ohne personenbezogene Ereignisdiagnose'))
    if fight.get('partial') or fight.get('coverage_incomplete'):notes.append(_tr('Kampferfassung teilweise/unvollständig'))
    if fight.get('group_coverage_confirmed') is False:notes.append(_tr('Gruppen-/Raidliste unbestätigt oder unvollständig'))
    if fight.get('tracking_scope')=='self':notes.append(_tr('World-/Abyssboss · nur eigener Spieler'))
    elif fight.get('boss_type')=='world_boss' or fight.get('area_kind')=='field':notes.append(_tr('Worldboss/Open World weiterhin offen; nur beobachtete Mitglieder'))
    if fight.get('healing_coverage_incomplete'):notes.append(_tr('Ungeklärte Regeneration nicht als HP-Heilung gewertet'))
    return {'status':status,'label':LABELS[status],'notes':notes,'damage_events':damage,'healing_events':heals,'casts':casts,'hit_notices':notices,'completeness_confirmed':False}

def quality_text(actor,fight):
    q=player_quality(actor,fight)
    return q['label']+(' · '+'; '.join(q['notes']) if q['notes'] else '')+_tr(' · Vollständigkeit nicht bestätigt')


def coverage_notice(fight):
    issues=fight.get('quality_issues',{});parts=[]
    from .observation_quality import sparse_damage_coverage
    if sparse_damage_coverage(fight):parts.append(_tr('Direkte Schadensbeträge vieler Spieler fehlen; DPS und Anteile sind unvollständig.'))
    periodic=sum(n for key,n in issues.items() if key.startswith('periodic:'))
    parser=sum(n for key,n in issues.items() if key.startswith('damage_parser:') or key=='damage_scope_unknown')
    if periodic:parts.append(_tr('{0} periodische Ereignisse nicht klassifiziert',periodic))
    if parser:parts.append(_tr('{0} Schadensmeldungen nicht dekodiert',parser))
    if issues.get('unresolved_owner'):parts.append(_tr('{0} Begleiter-Ereignisse ohne Besitzer',issues['unresolved_owner']))
    if issues.get('worldboss_damage_unconfirmed'):parts.append(_tr('{0} Spieler ohne erfassten Schadensbetrag',issues['worldboss_damage_unconfirmed']))
    if issues.get('identity_deferred'):parts.append(_tr('Spielerzuordnung verzögert; Treffer nachgetragen'))
    return _tr('Erfassung unvollständig: ')+('; '.join(parts) if parts else _tr('Details unter Datenqualität.'))
