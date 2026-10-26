"""Missing observed amounts are not evidence of zero contribution."""

def sparse_damage_coverage(fight):
    if fight.get('metric') or fight.get('tracking_scope')=='self':return False
    if fight.get('damage_coverage') in ('sparse_worldboss_amounts','sparse_raid_amounts'):return True
    actors=fight.get('actors',[])
    # A known boss can lack a map/category label. Do not let missing location
    # metadata hide a large-raid capture problem or invent a location instead.
    if len(actors)<10 or not (fight.get('boss_name') or fight.get('boss_id') or fight.get('boss_template')):return False
    # Landed-hit notices are explicit activity evidence, but carry no amount.
    if sum((a.get('hit_notices') or 0)>0 and not a.get('hits') for a in actors)>=5:return True
    direct=sum((a.get('damage') or 0)>0 and (a.get('hits') or 0)>0 for a in actors)
    periodic=sum((a.get('damage') or 0)>0 and not a.get('hits') and (a.get('dot_ticks') or 0)>0 for a in actors)
    if direct>0 and periodic>=5 and direct*4<=periodic:return True
    active=[a for a in actors if (a.get('casts') or 0)>=10]
    amounts=[a.get('damage') or 0 for a in actors];total=sum(amounts)
    return len(active)>=6 and sum(not a.get('damage') for a in active)>=5 and total>0 and max(amounts)>=total*.95

def damage_amount_partial(actor,fight):
    return sparse_damage_coverage(fight) and (actor.get('damage') or 0)>0 and not actor.get('hits') and (actor.get('dot_ticks') or 0)>0

def damage_amount_missing(actor,fight):
    if fight.get('tracking_scope')=='self':return False
    if fight.get('metric') or not (fight.get('boss_type')=='world_boss' or fight.get('area_kind')=='field' or sparse_damage_coverage(fight)):
        return False
    if actor.get('damage')!=0:return False
    evidence=actor.get('data_quality',{})
    events=evidence.get('damage_events') if isinstance(evidence,dict) else None
    return not (type(events) is int and events>0)

def missing_damage_actors(fight):
    return [a for a in fight.get('actors',[]) if damage_amount_missing(a,fight)]

def annotate_worldboss(fight):
    if sparse_damage_coverage(fight):
        world=fight.get('boss_type')=='world_boss'
        fight['damage_coverage']='sparse_worldboss_amounts' if world else 'sparse_raid_amounts'
        fight.setdefault('quality_issues',{})['worldboss_damage_sparse' if world else 'raid_damage_sparse']=1
        fight['coverage_incomplete']=True;fight['partial']=True
        for actor in fight.get('actors',[]):
            if damage_amount_partial(actor,fight):actor['damage_observation']='periodic_amounts_only'
    missing=missing_damage_actors(fight)
    if missing:
        fight['quality_issues']['worldboss_damage_unconfirmed']=len(missing)
        fight['coverage_incomplete']=True;fight['partial']=True
        for actor in missing:actor['damage_observation']='no_amount_observed'
    return fight
