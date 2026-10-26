"""Presentation-only projections; original damage reports are never modified."""

from .language import TranslatedDict
METRICS=TranslatedDict({'damage':'Schaden','healing':'Heilung','other_healing':'Fremdheilung','self_healing':'Selbstheilung'})

def metric_report(report,metric='damage'):
    from .personal_boss import personal_report
    report=personal_report(report)
    from .healing import observed_amount
    if metric not in METRICS or metric=='damage':return report
    result={**report,'fights':[]}
    for original in report.get('fights',[]):
        fight=dict(original);result['fights'].append(fight)
        if original.get('damage_scope'):
            fight['start_ms']=original.get('scope_original_start_ms',original['start_ms'])
            fight['last_damage_ms']=original.get('scope_original_last_damage_ms',original.get('last_damage_ms'))
        actors=[];seconds=max(1,fight.get('healing_seconds',fight.get('seconds',1)))
        for actor in fight.get('actors',[]):
            actor=dict(actor)
            value=observed_amount(original,actor,metric)
            if value is None:continue # older logs have no self/other split
            actor['damage']=value;actor['dps']=value/seconds if fight.get('integrity','ok')=='ok' else None
            actors.append(actor)
        fight['actors']=sorted(actors,key=lambda a:a['damage'],reverse=True)
        fight['total_damage']=sum(a['damage'] for a in actors) if fight.get('integrity','ok')=='ok' else None
        fight['dps']=fight['total_damage']/seconds if fight['total_damage'] is not None else None
        fight['seconds']=seconds
        fight['timeline']=[{'second':r['second'],'damage':r.get(metric,0)} for r in fight.get('healing_timeline',[])]
        fight['metric']=metric;fight['metric_label']=METRICS[metric]
        fight['healing_legacy']=not fight.get('healing_observed',False)
        if fight.get('healing_coverage_incomplete'):fight['partial']=True;fight['coverage_incomplete']=True
        fight['target_hp']=None;fight['target_max_hp']=0
    return result
