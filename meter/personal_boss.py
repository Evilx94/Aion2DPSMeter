"""Personal-only public-boss views; never estimate other players' amounts."""
from collections import Counter
from copy import deepcopy
from functools import lru_cache

@lru_cache(maxsize=1)
def runtime_catalog():
    from .core.encounters import EncounterCatalog
    return EncounterCatalog.for_runtime(None)

def public_boss(fight,catalog=None):
    # Explicit instance context takes precedence over field/template fallbacks.
    if fight.get('dungeon_name') or fight.get('area_kind')=='dungeon' or fight.get('boss_type')=='dungeon_boss':return False
    if fight.get('boss_type') in ('world_boss','abyss_boss'):return True
    template=fight.get('boss_template')
    if not (template or fight.get('boss_id') or fight.get('boss_name')):return False
    if fight.get('area_kind')=='field':return True
    locations=(catalog or runtime_catalog()).locations_for(template)
    return bool(locations) and all(item.kind=='field' for item in locations)

def personal_fight(fight,catalog=None,entries=None):
    if not public_boss(fight,catalog):return fight
    result=deepcopy(fight)
    own=fight.get('self_identity',{}).get('id')
    own=own if type(own) is int and own>0 else None
    result.update(tracking_scope='self',damage_coverage='personal_observed',group_state='self_only',group_coverage_confirmed=None)
    result['actors']=[a for a in result.get('actors',[]) if own is not None and a.get('id')==own]
    for key in ('skills','cast_usage','buffs'):
        result[key]=[r for r in result.get(key,[]) if own is not None and r.get('actor')==own]
    result['group_roster']=[];result['group_identity']={};result['unassigned_actors']=[]
    valid=result.get('integrity','ok')=='ok'
    total=sum(a.get('damage',0) for a in result['actors'])
    healing=sum(a.get('healing',0) for a in result['actors'])
    result['total_damage']=total if valid else None
    result['dps']=total/max(1,result.get('seconds',1)) if valid else None
    result['total_healing']=healing if valid else None
    result['hps']=healing/max(1,result.get('healing_seconds',result.get('seconds',1))) if valid else None
    result['healing_coverage_incomplete']=any(r.get('unclassified_recovery',0)>0 for r in result['skills'])
    if fight.get('tracking_scope')!='self':result['unclassified_recovery_events']=None
    # Sparse raid warnings do not describe the new personal scope. Keep capture,
    # parser and integrity diagnostics, including their existing partial flags.
    for key in ('worldboss_damage_sparse','raid_damage_sparse','worldboss_damage_unconfirmed'):
        result.get('quality_issues',{}).pop(key,None)
    if entries is not None:
        result['coverage_incomplete']=bool(result.get('quality_issues'))
        result['partial']=bool(result.get('capture_partial') or result['coverage_incomplete'])
        from .healing import RECOVERY_EXCLUSIONS
        timeline=Counter();heals={};targets=Counter();recovery_events=0
        for e in entries:
            if own is None or e.actor!=own:continue
            second=(e.time-result['start_ms'])//1000
            if e.kind=='damage':timeline[second]+=e.damage;targets[e.target]+=e.damage
            elif e.kind=='heal' and e.skill in RECOVERY_EXCLUSIONS:recovery_events+=1
            elif e.kind=='heal':
                row=heals.setdefault(second,{'second':second,'healing':0,'self_healing':0,'other_healing':0})
                row['healing']+=e.damage;row['self_healing' if e.healing_scope=='self' else 'other_healing']+=e.damage
        result['unclassified_recovery_events']=recovery_events
        result['healing_coverage_incomplete']=bool(recovery_events)
        result['timeline']=[{'second':s,'damage':v} for s,v in sorted(timeline.items())]
        result['healing_timeline']=[r for s,r in sorted(heals.items())]
        result['targets']=[{**r,'damage':targets[r['id']]} for r in result.get('targets',[]) if r['id'] in targets]
        result['personal_timeline_available']=True
    elif not fight.get('tracking_scope')=='self':
        # Historical aggregate timelines cannot be separated by player.
        result['timeline']=[];result['healing_timeline']=[];result['targets']=[]
        result['personal_timeline_available']=False
    return result

def personal_report(report):
    fights=[personal_fight(f) for f in report.get('fights',[])]
    if not any(a is not b for a,b in zip(fights,report.get('fights',[]))):return report
    result={**report,'fights':fights}
    if fights and fights[-1].get('tracking_scope')=='self':
        result.update(group_state='self_only',roster=[],group_identity={})
    return result
