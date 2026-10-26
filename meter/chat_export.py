"""Plain-text combat summaries for deliberate clipboard sharing."""
from .language import tr as _tr,decimal
from math import isfinite
from .overlay import actor_label, number
from .equipment import equipment_text

def clean(value):
    return ' '.join(str(value or '').split())

def run_identity(report):
    fights=report.get('fights',[])
    if not fights:return None
    fight=fights[-1]
    session=report.get('session',{}).get('id')
    run=fight.get('run_key')
    if not session or run is None or not fight.get('dungeon_name'):return None
    return session,run,fight.get('map_id'),fight['dungeon_name']

def dungeon_reports(reports,selected):
    from .encounter_scope import project_report
    key=run_identity(selected)
    if key is None:return []
    unique={}
    for report in reports:
        if run_identity(report)!=key:continue
        fight=report['fights'][-1]
        if not (fight.get('boss_template') or fight.get('boss_id') or fight.get('boss_name')):continue
        scoped=project_report(report,'boss')
        if scoped:unique[(report.get('session',{}).get('id'),fight.get('id'))]=scoped
    return sorted(unique.values(),key=lambda r:(r['fights'][-1].get('start_ms',0),str(r['fights'][-1].get('id'))))

def fight_lines(report):
    from .personal_boss import personal_report
    report=personal_report(report)
    fight=report['fights'][-1]
    title=clean(fight.get('boss_name') or fight.get('target_name') or _tr('Kampf'))
    lines=[title]
    if fight.get('tracking_scope')=='self':lines.append(_tr('World-/Abyssboss · nur eigener Spieler'))
    if fight.get('scope_note'):lines.append(fight['scope_note'])
    if fight.get('manual_outcome') or fight.get('reason')=='target_reset':
        from .encounter_history import outcome
        lines.append(outcome(fight))
    if fight.get('integrity','ok')!='ok':
        return lines+[_tr('Auswertung nicht verlässlich – keine Schadenswerte.')]
    actors=[]
    for actor in fight.get('actors',[]):
        damage=actor.get('damage')
        if type(damage) not in (int,float) or not isfinite(damage) or damage<0:continue
        actors.append(actor)
    if not actors:return lines+[_tr('Keine erfassten Schadenswerte.')]
    total=fight.get('total_damage')
    if type(total) not in (int,float) or not isfinite(total) or total<0:
        total=sum(a['damage'] for a in actors)
    if fight.get('partial') or fight.get('coverage_incomplete') or report.get('coverage_incomplete'):
        lines.append(_tr('Teilausschnitt / unvollständige Erfassung'))
    elif fight.get('reason')=='active':lines.append(_tr('Laufender Kampf – Zwischenstand'))
    if fight.get('group_coverage_confirmed') is False:
        lines.append(_tr('Gruppen-/Raidliste fehlt oder ist unvollständig · Anteile beziehen sich nur auf erfasste Spieler.'))
    from .observation_quality import sparse_damage_coverage
    if sparse_damage_coverage(fight):
        lines.append(_tr('Direkte Schadensbeträge vieler Spieler fehlen; DPS und Anteile sind unvollständig.'))
    elif fight.get('tracking_scope')!='self' and fight.get('boss_type')=='world_boss':lines.append(_tr('Worldboss: Werte der erfassten Gruppe/des Raids, keine Gesamtwertung aller Angreifer.'))
    from .observation_quality import damage_amount_missing
    for actor in sorted(actors,key=lambda a:(-a['damage'],str(a.get('id')))):
        name=clean(actor_label(actor,fight,report))
        if fight.get('tracking_scope')=='self':
            lines.append(_tr('{0}: {1} Schaden · {2} DPS',name,number(actor['damage']),number(actor.get('dps'))))
            continue
        if damage_amount_missing(actor,fight):
            lines.append(_tr('{0}: kein Schadensbetrag erfasst · Beitrag unbekannt',name))
            continue
        if sparse_damage_coverage(fight):
            stats=equipment_text(actor,False)
            lines.append(_tr('{0}: {1} erfasster Schaden · Anteil unbekannt',name,number(actor['damage']))+(' · '+stats if stats else ''))
            continue
        share=decimal(f"{100*actor['damage']/total:.1f}") if total else decimal('0.0')
        stats=equipment_text(actor,False)
        lines.append(_tr('{0}: {1} Schaden · {2} %' ,name,number(actor['damage']),share)+(' · '+stats if stats else ''))
    return lines

def fight_text(report):
    if not report.get('fights'):return ''
    from .personal_boss import personal_report
    report=personal_report(report)
    fight=report['fights'][-1]
    area=clean(fight.get('dungeon_name') or fight.get('region_name'))
    header='AION 2 · '+area if area else ('AION 2' if fight.get('tracking_scope')=='self' else _tr('AION 2 · Gruppenschaden'))
    return '\n'.join([header]+fight_lines(report))

def healing_text(report,metric='healing'):
    from .metrics import metric_report,METRICS
    projected=metric_report(report,metric)
    if not projected.get('fights'):return ''
    fight=projected['fights'][-1];unit=METRICS[metric]
    lines=['AION 2 · '+clean(fight.get('dungeon_name') or fight.get('region_name') or unit),clean(fight.get('boss_name') or fight.get('target_name') or _tr('Kampf'))+' · '+unit]
    if fight.get('integrity','ok')!='ok':return '\n'.join(lines+[_tr('Auswertung nicht verlässlich – keine Heilungswerte.')])
    lines.append(_tr('Beobachtete Heilung · effektive Heilung/Überheilung unbestätigt'))
    if fight.get('tracking_scope')=='self':lines.append(_tr('World-/Abyssboss · nur eigener Spieler'))
    total=fight.get('total_damage') or 0
    if fight.get('partial') or fight.get('coverage_incomplete'):lines.append(_tr('Teilausschnitt / unvollständige Erfassung'))
    elif fight.get('reason')=='active':lines.append(_tr('Laufender Kampf – Zwischenstand'))
    if fight.get('group_coverage_confirmed') is False:lines.append(_tr('Gruppen-/Raidliste fehlt oder ist unvollständig · nur erfasste Spieler.'))
    if fight.get('healing_legacy'):lines.append(_tr('Älterer Log: Selbst-/Fremdaufteilung gegebenenfalls unbekannt'))
    for actor in fight.get('actors',[]):
        share=100*actor['damage']/total if total else 0
        share_text=decimal(f'{share:.1f}')
        portion='' if fight.get('tracking_scope')=='self' else f' · {share_text} %'
        lines.append(f"{clean(actor_label(actor,fight,report))}: {number(actor['damage'])} {unit}{portion} · {number(actor['dps'])} HPS")
    return '\n'.join(lines)

def dungeon_text(reports,selected):
    selected_reports=dungeon_reports(reports,selected)
    if not selected_reports:return ''
    name=clean(selected['fights'][-1]['dungeon_name'])
    lines=['AION 2 · '+name,_tr('Aufgezeichnete Bosskämpfe')]
    # These numbers count recorded encounters, not fixed dungeon boss positions.
    for index,report in enumerate(selected_reports,1):
        block=fight_lines(report)
        lines.extend(['',_tr('Bosskampf {0} · {1}' ,index,block[0])]+block[1:])
    return '\n'.join(lines)
