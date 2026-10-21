"""Local, editable wall-clock event plans. No game-state or spawn claims."""
from copy import deepcopy
from PySide6.QtCore import QDateTime,QTime,QTimeZone

SOURCE='https://shugo.gg/timers'
CATEGORIES=('Shugo','Boss','Rift','PvP','Sonstiges')
IRREGULAR_WORLD_BOSSES=frozenset(('gartua','garuta','lagta','vishwada','kashapa','kashpa','linx','inx','dartan'))
FIXED_BOSSES=frozenset(('kaira','abyss_bosses','nahma'))

def without_irregular_bosses(rows):
    return [row for row in rows if not isinstance(row,dict) or row.get('id') not in IRREGULAR_WORLD_BOSSES]
def merchant_event():
    return dict(id='black_cloud_merchant',name='Black Cloud Merchant · Refresh',category='Sonstiges',
                times=[f'{hour:02}:00' for hour in range(24)],days=list(range(7)),minutes=0,
                enabled=True,source='https://talentbuilds.com/aion2/blackcloudmerchant',
                checked='2026-10-19',status='community')

def defaults():
    def event(key,name,category,times,days=range(7),minutes=0):
        return dict(id=key,name=name,category=category,times=times,days=list(days),minutes=minutes,
                    enabled=True,source=SOURCE,checked='2026-10-15',status='community')
    rows=[event('shugo','Shugo Festival','Shugo',[f'{h:02}:00' for h in range(24)],minutes=10),
          event('rift','Rift · Portaleintritt','Rift',[f'{h:02}:00' for h in range(2,24,3)],minutes=10),
          event('invasion','Dimensionsinvasion','Sonstiges',[f'{h:02}:30' for h in range(24)],minutes=15),
          event('kaira','Watcher Kaira','Boss',[f'{h:02}:00' for h in range(1,24,3)],minutes=30),
          event('siege','Artefaktbelagerung','PvP',['21:00'],[0,3,5],30),
          event('abyss_bosses','Abyss-Bosse','Boss',['21:30'],[0,3,5],30),
          event('nahma','Guardian Lord Nahma','Boss',['21:00'],[4,6],30)]
    for key,label,hour,minutes in [('arena_day','Arena of Tactics · tagsüber','11:00',180),('arena_evening','Arena of Tactics · abends','19:00',120)]:
        r=event(key,label,'PvP',[hour],minutes=minutes);r['source']='https://aion2data.com/timers';rows.append(r)
    rows.append(merchant_event())
    from .language import migrate_event_names
    return migrate_event_names(rows)

def validate(rows,language='en'):
    from .language import text
    def t(en,de):return text(language,en,de)
    if not isinstance(rows,list) or len(rows)>60:raise ValueError(t('Up to 60 events allowed.','Maximal 60 Events erlaubt.'))
    result=[];ids=set()
    for row in rows:
        if not isinstance(row,dict):raise ValueError(t('Invalid event.','Ungültiges Event.'))
        key=row.get('id');name=row.get('name');times=row.get('times');days=row.get('days')
        if not isinstance(key,str) or not key or key in ids:raise ValueError(t('Missing or duplicate event ID.','Event-ID fehlt oder ist doppelt.'))
        if not isinstance(name,str) or not 1<=len(name.strip())<=80:raise ValueError(t('Event name: 1–80 characters.','Eventname: 1–80 Zeichen.'))
        if row.get('category') not in CATEGORIES:raise ValueError(t('Unknown event type.','Unbekannte Eventart.'))
        if not isinstance(times,list) or len(times)>48 or any(not isinstance(value,str) or len(value)!=5 or not QTime.fromString(value,'HH:mm').isValid() for value in times):raise ValueError(t('Enter times as HH:mm, e.g. 14:00, 17:00.','Zeiten als HH:mm eintragen, z. B. 14:00, 17:00.'))
        if not isinstance(days,list) or not days or any(type(d) is not int or not 0<=d<=6 for d in days):raise ValueError(t('Days: 1 to 7 (Monday to Sunday).','Wochentage: 1 bis 7 (Montag bis Sonntag).'))
        if type(row.get('minutes')) is not int or not 0<=row['minutes']<=1440:raise ValueError(t('Window: 0 to 1440 minutes.','Zeitfenster: 0 bis 1440 Minuten.'))
        if type(row.get('enabled')) is not bool:raise ValueError(t('Invalid enabled state.','Ungültige Aktivierung.'))
        if row['enabled'] and not times:raise ValueError(name+t(': enter at least one start time.',': mindestens eine Startzeit eintragen.'))
        ids.add(key);clean=deepcopy(row);clean.update(name=name.strip(),times=sorted(set(times)),days=sorted(set(days)))
        result.append(clean)
    return result

def schedule(rows,now,zone_id='Europe/Berlin'):
    """Next planned start per enabled event; durations never delay rollover."""
    now=int(now)
    zone=QTimeZone(zone_id.encode('ascii'))
    if not zone.isValid():raise ValueError('Unbekannte Zeitzone.')
    today=QDateTime.fromSecsSinceEpoch(int(now),zone).date();result=[]
    for row in validate(without_irregular_bosses(rows)):
        if not row['enabled']:continue
        candidates=[]
        for offset in range(0,9):
            day=today.addDays(offset)
            if day.dayOfWeek()-1 not in row['days']:continue
            for value in row['times']:
                time=QTime.fromString(value,'HH:mm')
                dt=QDateTime(day,time,zone,QDateTime.TransitionResolution.PreferBefore)
                # A skipped spring wall-clock time is not a scheduled 03:00 event.
                if not dt.isValid() or dt.date()!=day or dt.time()!=time:continue
                start=dt.toSecsSinceEpoch();end=start+row['minutes']*60
                if start>=now:candidates.append((start,end))
        if not candidates:continue
        start,end=min(candidates)
        result.append({**row,'start':start,'end':end,'active':False,'remaining':start-now})
    return sorted(result,key=lambda r:(r['start'],r['name']))

def countdown(seconds):
    seconds=max(0,int(seconds));days,seconds=divmod(seconds,86400);hours,seconds=divmod(seconds,3600);minutes,seconds=divmod(seconds,60)
    return (f'{days}d ' if days else '')+f'{hours:02}:{minutes:02}:{seconds:02}'
