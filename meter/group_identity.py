"""Explain roster-to-entity coverage without granting any authorization."""
def identity_status(world):
    rows=world.party_records;resolved=[];pending=[];ambiguous=[]
    people=[p for p in world.people.values() if p.confirmed and world.authorized(p.entity)] if world.party_trusted else []
    for row in rows:
        candidates=[]
        for person in people:
            if person.name!=row['name']:continue
            server=world.player_server(person.entity)
            linked=server==row['server']
            if not linked and person.entity==world.self_entity and not server:
                # Known local identity can be counted as self without assigning
                # any other entity or guessing among equal roster names.
                linked=sum(r['name']==person.name for r in rows)==1 and bool(person.class_name) and person.class_name==row.get('class')
            if linked:candidates.append(person.entity)
        if len(candidates)==1:resolved.append(row['name'])
        elif candidates:ambiguous.append(row['name'])
        else:pending.append(row['name'])
    return {'total':len(rows),'resolved':len(resolved),'pending':len(pending),'ambiguous':len(ambiguous),'pending_names':pending,'ambiguous_names':ambiguous,'trusted':bool(world.party_trusted)}
