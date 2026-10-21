"""Read-only boss/trash projections; old logs never acquire invented splits."""
from copy import deepcopy
from .language import tr

def section_keys(fight):
    return [key for key in ('boss','trash','unknown') if fight.get('damage_sections',{}).get(key)]

def encounter_kind(fight):
    keys=section_keys(fight)
    if len(keys)>1:return 'mixed'
    if keys:return keys[0]
    if fight.get('boss_id') or fight.get('boss_template') or fight.get('boss_name'):return 'boss'
    targets=fight.get('targets',[])
    if targets and all(t.get('template') and t.get('name') and t.get('is_boss') is False for t in targets):return 'trash'
    return 'unknown'

def scope_label(key):
    return {'all':tr('Alle Kämpfe'),'boss':tr('Boss-Schaden'),'trash':tr('Trash-Schaden'),'unknown':tr('Unklassifiziert'),'mixed':tr('Gemischt')}[key]

def project_report(report,scope):
    if scope=='all':return deepcopy(report)
    if not report.get('fights'):return None
    original=report['fights'][-1];section=original.get('damage_sections',{}).get(scope)
    if not section:
        if encounter_kind(original)!=scope:return None
        result=deepcopy(report)
        if scope=='boss':result['fights'][-1]['scope_note']=tr('Älterer Log: Boss-/Trash-Schaden nicht nachträglich trennbar.')
        return result
    result=deepcopy(report);fight=result['fights'][-1];fight['damage_scope']=scope
    fight['scope_original_start_ms']=original['start_ms'];fight['scope_original_last_damage_ms']=original.get('last_damage_ms')
    amounts={a['id']:a for a in section['actors']}
    for actor in fight.get('actors',[]):
        row=amounts.get(actor['id'],{})
        for field in ('damage','hits','crits','dot_ticks','dot_damage','summon_damage'):actor[field]=row.get(field,0)
        actor['dps']=row.get('dps',0) if fight.get('integrity','ok')=='ok' else None
        actor.setdefault('data_quality',{})['damage_events']=row.get('damage_events',0)
    fight['actors'].sort(key=lambda a:a['damage'],reverse=True)
    skill_amounts={(r['actor'],r['skill']):r for r in section['skills']}
    for row in fight.get('skills',[]):
        scoped=skill_amounts.get((row['actor'],row['skill']),{})
        for field in ('damage','hits','crits','dot_ticks','summon_damage'):row[field]=scoped.get(field,0)
    for field in ('start_ms','last_damage_ms','seconds','total_damage','dps','timeline'):fight[field]=deepcopy(section[field])
    if fight.get('integrity','ok')!='ok':fight.update(total_damage=None,dps=None)
    targets={t['id']:t for t in original.get('targets',[])}
    fight['targets']=[dict(targets.get(t['id'],{}),**t) for t in section['targets']]
    primary=fight['targets'][0] if fight['targets'] else {}
    fight.update(target_id=primary.get('id'),target_name=primary.get('name',''),target_template=primary.get('template'),target_hp=None,target_max_hp=0)
    if scope!='boss':fight.update(boss_id=None,boss_name='',boss_template=None,boss_type='',boss_index=None)
    fight['scope_note']=tr('Schaden nach Zieltyp getrennt; Heilung, Casts und Buffs gelten für den gesamten Kampfabschnitt.')
    return result
