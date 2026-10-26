"""Presentation of observations excluded from confirmed group totals."""
from .language import tr
from .overlay import number

def observation_text(report):
    fights=report.get('fights',[])
    if not fights:return ''
    rows=fights[-1].get('unassigned_actors',[])
    if not rows:return ''
    lines=[]
    for actor in rows[:8]:
        label=actor.get('name') or tr('Spieler ?')
        value=tr('{0} Schaden · {1} DPS · {2} Heilung',number(actor.get('damage',0)),number(actor.get('dps')),number(actor.get('healing',0)))
        if actor.get('unreliable'):value=tr('Paketkonflikt · Werte nicht verlässlich')
        lines.append(f"{label} · Entity {actor['id']} · {actor.get('class') or '?'} · {value}")
    if len(rows)>8:lines.append(tr('Weitere nicht zugeordnete Entities: {0}',len(rows)-8))
    lines.append(tr('Separat erfasst; nicht in Gruppenschaden, Anteilen oder Chattext enthalten.'))
    return '\n'.join(lines)


def provisional_report(report):
    """Add explicitly unconfirmed dungeon rows to bars, never to group totals.

    Called after the damage/healing metric projection. No cast/skill ownership,
    name or membership is inferred from a class or a shared target.
    """
    fights=report.get('fights',[])
    if not fights:return report
    original=fights[-1]
    from .personal_boss import public_boss
    if original.get('tracking_scope')=='self' or original.get('provisional_rows') or public_boss(original):return report
    dungeon=original.get('dungeon_name') or original.get('area_kind')=='dungeon'
    # A late-start capture can lack map/spawn metadata altogether. These rows
    # remain unconfirmed observations; this does not classify the area as dungeon.
    unknown_pve=original.get('area_kind') in (None,'unknown') and original.get('combat_type')=='pve'
    if not (dungeon or unknown_pve):return report
    metric=original.get('metric','damage')
    # Do not project unidentified recovery/resource effects as confirmed healing.
    if metric!='damage':return report
    additions=[]
    scoped=original.get('damage_scope') not in (None,'all') and metric=='damage'
    targets={r['id'] for r in original.get('targets',[])}
    for row in original.get('unassigned_actors',[]):
        value=row.get(metric,0);rate=row.get('dps' if metric=='damage' else 'hps')
        if scoped:
            if 'damage_targets' not in row:continue # no invented historical split
            selected=[t for t in row['damage_targets'] if t['id'] in targets]
            value=sum(t['damage'] for t in selected)
            seconds=max(1,(max([original.get('last_damage_ms',original['start_ms'])]+[t['last_ms'] for t in selected])-original['start_ms'])/1000)
            rate=value/seconds if original.get('integrity','ok')=='ok' and not row.get('unreliable') else None
        if value<=0:continue
        additions.append({**row,'damage':value,'dps':rate,'provisional_membership':True,'name_source':'unconfirmed_group'})
    if not additions:return report
    fight={**original,'actors':sorted(list(original.get('actors',[]))+additions,key=lambda a:-a.get('damage',0)),
           'provisional_rows':len(additions),'shares_unavailable':True}
    return {**report,'fights':list(fights[:-1])+[fight]}
