"""Partition accepted damage by explicitly identified target, not spawn heuristics."""
from collections import Counter

def target_category(npc):
    if npc and npc.is_boss:return 'boss'
    if npc and npc.template and npc.name_source:return 'trash'
    return 'unknown'

def damage_sections(entries,valid=True):
    result={};groups={}
    for entry in entries:
        if entry.kind=='damage':groups.setdefault(entry.target_category,[]).append(entry)
    for category in ('boss','trash','unknown'):
        selected=groups.get(category,[])
        if not selected:continue
        start=min(e.time for e in selected);last=max(e.time for e in selected);seconds=max(1,(last-start)/1000)
        amounts=Counter();timeline=Counter();targets=Counter();actors={};skills={}
        for e in selected:
            amounts[e.actor]+=e.damage;timeline[(e.time-start)//1000]+=e.damage;targets[e.target]+=e.damage
            for key,table in ((e.actor,actors),((e.actor,e.skill),skills)):
                row=table.get(key)
                if row is None:row=table[key]=dict(damage=0,hits=0,crits=0,dot_ticks=0,dot_damage=0,summon_damage=0,damage_events=0)
                row['damage']+=e.damage;row['hits']+=0 if e.periodic else e.hits;row['crits']+=int(e.critical)
                row['dot_ticks']+=int(e.periodic);row['dot_damage']+=e.damage if e.periodic else 0
                row['summon_damage']+=e.damage if e.source_entity and e.source_entity!=e.actor else 0;row['damage_events']+=1
        result[category]=dict(start_ms=start,last_damage_ms=last,seconds=seconds,total_damage=sum(amounts.values()) if valid else None,
            dps=sum(amounts.values())/seconds if valid else None,
            actors=[dict(id=actor,**row,dps=row['damage']/seconds if valid else None) for actor,row in actors.items()],
            skills=[dict(actor=actor,skill=skill,**row) for (actor,skill),row in skills.items()],
            targets=[dict(id=target,damage=amount) for target,amount in targets.items()],
            timeline=[dict(second=second,damage=amount) for second,amount in sorted(timeline.items())])
    return result
