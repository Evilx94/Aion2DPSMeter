"""Portable runtime preferences, no machine-specific adapter or character defaults."""
from pathlib import Path
import os,json
from copy import deepcopy
from .events import defaults as event_defaults

DEFAULTS={'archive_combat_days':0,'archive_capture_days':0,'display_metric':'damage','palette':'Klassenfarben','opacity':88,'graph_opacity':88,'overlay':False,'graph_overlay':False,
          'update_prereleases':False,'language':'en','appearance':{},'event_timezone':'Europe/Berlin','event_schedule_timezone':'Europe/Berlin',
          'dungeon_scope':'all','pets_owned':[],
          'event_overlay':False,'event_opacity':88,'event_attached':False,'event_locked':False,'event_position':[],
          'event_free_position':[],'event_size':[300,125],'event_schedule':event_defaults(),'event_layout':0,'event_shop_timer_added':False,'event_fixed_bosses_added':False,'event_utc_resets_added':False,
          'attached':False,'attachment_mode':'Frei schwebend','click_through':False,'save_combat':True,'save_packets':False,
          'save_debug':True,'log_folder':'','character_name':'','character_identity':{},'manual_identity':False,'accent':'#71ddc4','class_colors':{},'dps_position':[],'graph_position':[],
          'dps_free_position':[],'graph_free_position':[],'dps_size':[350,260],'graph_size':[350,220],
          'dps_locked':False,'graph_locked':False,'dps_font_size':14,
          'window_size':[680,730],'window_position':[],'track_pvp':True,'skill_names_file':'','skill_names_enabled':True,'schema_version':1}

def runtime_directory(base=None):
    override=os.environ.get('AION2_METER_DATA_DIR')
    if override:return Path(override)
    return Path(os.environ.get('LOCALAPPDATA',str(Path.cwd())))/'Aion2Meter'

class Preferences:
    def __init__(self,directory):
        self.directory=Path(directory)
        self.path=self.directory/'preferences.json'
        self.values=deepcopy(DEFAULTS)
        try:
            data=json.loads(self.path.read_text(encoding='utf-8'))
            if isinstance(data,dict):
                for key,value in data.items():
                    if key in DEFAULTS and type(value) is type(DEFAULTS[key]):self.values[key]=value
                if 'event_opacity' not in data:self.values['event_opacity']=self.values['opacity']
                if 'graph_opacity' not in data:self.values['graph_opacity']=self.values['opacity']
        except (OSError,ValueError):pass
        loaded_schedule=deepcopy(self.values['event_schedule'])
        loaded_fixed_bosses=self.values['event_fixed_bosses_added']
        loaded_utc_resets=self.values['event_utc_resets_added']
        self.validate();self._saved=deepcopy(self.values)
        # Keep schedule migrations dirty so disk merging cannot undo them.
        self._saved['event_schedule']=loaded_schedule
        self._saved['event_fixed_bosses_added']=loaded_fixed_bosses
        self._saved['event_utc_resets_added']=loaded_utc_resets
    def validate(self):
        import math
        from .appearance import clean_appearance,valid_color
        from .clock_zones import valid_zone
        self.values['appearance']=clean_appearance(self.values['appearance'])
        for key in ('event_timezone','event_schedule_timezone'):
            if not valid_zone(self.values[key]):self.values[key]='Europe/Berlin'
        if not valid_color(self.values['accent']):self.values['accent']=DEFAULTS['accent']
        self.values['class_colors']={key:value.lower() for key,value in self.values['class_colors'].items() if isinstance(key,str) and valid_color(value)}
        if self.values['event_layout']<2:
            self.values['event_size']=[300,125];self.values['event_layout']=2
        from .events import validate,without_irregular_bosses,FIXED_BOSSES
        self.values['event_schedule']=without_irregular_bosses(self.values['event_schedule'])
        try:self.values['event_schedule']=validate(self.values['event_schedule'])
        except ValueError:self.values['event_schedule']=event_defaults()
        if not self.values['event_fixed_bosses_added']:
            rows=self.values['event_schedule'];existing={row['id'] for row in rows}
            # Restore fixed bosses removed by the old blanket Boss filter.
            # A wholly custom or deliberately empty schedule stays custom.
            if existing & (FIXED_BOSSES|{'siege'}):
                for row in event_defaults():
                    if row['id'] in FIXED_BOSSES and row['id'] not in existing and len(rows)<60:rows.append(row)
            self.values['event_fixed_bosses_added']=True
        if not self.values['event_shop_timer_added']:
            from .events import merchant_event
            rows=self.values['event_schedule']
            if not any(row['id']=='black_cloud_merchant' for row in rows) and len(rows)<60:
                rows.append(merchant_event())
            self.values['event_shop_timer_added']=True
        if not self.values['event_utc_resets_added']:
            from .events import reset_events
            rows=self.values['event_schedule'];existing={row['id'] for row in rows}
            # Add resets once to a standard plan; keep custom/empty plans and
            # deliberate removals intact. Existing user reset times win.
            if existing & {'shugo','rift','siege','kaira'}:
                for row in reset_events():
                    if row['id'] not in existing and len(rows)<60:rows.append(row)
            self.values['event_utc_resets_added']=True
        from .language import migrate_event_names
        self.values['event_schedule']=migrate_event_names(self.values['event_schedule'])
        self.values['pets_owned']=sorted({key for key in self.values['pets_owned'] if isinstance(key,str) and 0<len(key)<=160})[:500]
        if self.values['language'] not in ('en','de'):self.values['language']='en'
        if self.values['dungeon_scope'] not in ('all','boss','trash','unknown'):self.values['dungeon_scope']='all'
        if self.values['display_metric'] not in ('damage','healing','self_healing','other_healing'):self.values['display_metric']='damage'
        for key in ('archive_combat_days','archive_capture_days'):self.values[key]=max(0,min(3650,self.values[key]))
        for key in ('opacity','graph_opacity','event_opacity'):self.values[key]=min(100,max(40,self.values[key]))
        self.values['dps_font_size']=min(24,max(8,self.values['dps_font_size']))
        for key in ('dps_position','graph_position','dps_free_position','graph_free_position','window_position','dps_size','graph_size','window_size','event_position','event_free_position','event_size'):
            pair=self.values[key]
            if len(pair)!=2 or any(type(v) not in (int,float) or not math.isfinite(v) for v in pair):
                self.values[key]=deepcopy(DEFAULTS[key]);continue
            pair=[int(round(v)) for v in pair]
            if key.endswith('_size'):
                minimum=(470,420) if key=='window_size' else ((260,115) if key=='event_size' else (280,180))
                pair=[min(2400,max(minimum[0],pair[0])),min(1600,max(minimum[1],pair[1]))]
            else:pair=[min(100000,max(-100000,v)) for v in pair]
            self.values[key]=pair
    def save(self):
        self.validate()
        try:
            current=json.loads(self.path.read_text(encoding='utf-8'))
            if isinstance(current,dict):
                for key,value in current.items():
                    if (key in DEFAULTS and type(value) is type(DEFAULTS[key])
                            and self.values[key]==self._saved.get(key) and value!=self._saved.get(key)):
                        self.values[key]=deepcopy(value)
        except (OSError,ValueError):pass
        self.validate()
        self.directory.mkdir(parents=True,exist_ok=True)
        temporary=self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps(self.values,indent=2,ensure_ascii=False),encoding='utf-8')
        temporary.replace(self.path);self._saved=deepcopy(self.values)
