"""Evidence labels describe observations, never certify complete player capture."""
from .language import tr as _tr
from .language import TranslatedDict
LABELS=TranslatedDict({'conflict':'Nicht verlässlich','partial':'Eingeschränkt','observed':'Werte beobachtet','activity_only':'Nur Casts / Trigger','unknown':'Keine Mengenbelege'})

def player_quality(actor,fight):
    stored=actor.get('data_quality',{})
    if not isinstance(stored,dict):stored={}
    damage=stored.get('damage_events');heals=stored.get('healing_events');casts=stored.get('casts',actor.get('casts'))
    raw_issues=stored.get('issues',{});issues=dict(raw_issues) if isinstance(raw_issues,dict) else {};notes=[]
    if fight.get('integrity','ok')!='ok':status='conflict';notes.append(_tr('Paketkonflikt oder ungültige Kampfdaten'))
    elif issues:status='partial'
    elif (actor.get('damage') or 0)>0 or (actor.get('healing') or 0)>0:status='observed'
    elif casts:status='activity_only';notes.append(_tr('Auslösungen ohne verwertbare Schadens-/Heilungsmenge'))
    else:status='unknown'
    if issues:notes.extend(f'{key}: {value}' for key,value in sorted(issues.items()))
    if not stored:notes.append(_tr('Älterer Log ohne personenbezogene Ereignisdiagnose'))
    if fight.get('partial') or fight.get('coverage_incomplete'):notes.append(_tr('Kampferfassung teilweise/unvollständig'))
    if fight.get('group_coverage_confirmed') is False:notes.append(_tr('Gruppen-/Raidliste unbestätigt oder unvollständig'))
    if fight.get('boss_type')=='world_boss' or fight.get('area_kind')=='field':notes.append(_tr('Worldboss/Open World weiterhin offen; nur beobachtete Mitglieder'))
    if fight.get('healing_coverage_incomplete'):notes.append(_tr('Ungeklärte Regeneration nicht als HP-Heilung gewertet'))
    return {'status':status,'label':LABELS[status],'notes':notes,'damage_events':damage,'healing_events':heals,'casts':casts,'completeness_confirmed':False}

def quality_text(actor,fight):
    q=player_quality(actor,fight)
    return q['label']+(' · '+'; '.join(q['notes']) if q['notes'] else '')+_tr(' · Vollständigkeit nicht bestätigt')
