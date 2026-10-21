"""Exact exclusions, never infer HP/MP from neighboring IDs or amount size."""
RECOVERY_EXCLUSIONS={
    16990004:'Observed regeneration; HP versus resource meaning unconfirmed. No neighboring-ID inference.',
}

def observed_amount(fight,actor,metric='healing'):
    value=actor.get(metric)
    if value is None or fight.get('healing_filtered'):return value
    excluded=sum(row.get(metric,0) for row in fight.get('skills',[]) if row.get('actor')==actor.get('id') and row.get('skill') in RECOVERY_EXCLUSIONS)
    return max(0,value-excluded)
