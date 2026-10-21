"""Local appearance settings. Colors never determine combat membership or metrics."""
import re
from copy import deepcopy

COMMON=dict(background='#17242e',text='#dce9f2',secondary='#a7bac8',header='#132029',controls='#263c48',control_text='#dce9f2',font_family='Segoe UI',font_size=10)
THEMES={
    'dps':dict(COMMON,bar_text='#f0f7fa',bar_detail='#d3e3eb',track='#354854',health='#ed9766',border='#c3e4ed',bar_opacity=38),
    'graph':dict(COMMON,accent='#71ddc4',grid='#31414c'),
    'clock':dict(COMMON,text='#a7bac7',event_text='#f3d77b',countdown='#71ddc4'),
}
LABELS={
 'background':('Background','Hintergrund'),'text':('Title / clock text','Titel- / Uhrtext'),'secondary':('Secondary text','Zusatztext'),
 'header':('Title bar','Titelleiste'),'controls':('Buttons','Schaltflächen'),'control_text':('Button text','Schaltflächentext'),
 'bar_text':('Names and DPS/HPS','Namen und DPS/HPS'),'bar_detail':('Class and damage details','Klasse und Schadensdetails'),
 'track':('HP bar background','LP-Balkenhintergrund'),'health':('HP bar','LP-Balken'),'border':('Own-player outline','Eigene Spielerumrandung'),
 'accent':('Graph line','Graphenlinie'),'grid':('Graph grid','Graphenraster'),
 'event_text':('Event name','Eventname'),'countdown':('Countdown','Countdown'),
}
ACCESSIBLE_COLORS=['#0072b2','#e69f00','#009e73','#cc79a7','#56b4e9','#d55e00','#f0e442','#999999','#ffffff']

def valid_color(value):return isinstance(value,str) and re.fullmatch(r'#[0-9a-fA-F]{6}',value) is not None

def clean_appearance(value):
    result={}
    if not isinstance(value,dict):return result
    for section,defaults in THEMES.items():
        rows=value.get(section)
        if not isinstance(rows,dict):continue
        result[section]={}
        for key,default in defaults.items():
            if key not in rows:continue
            v=rows[key]
            if key=='font_family':
                if isinstance(v,str) and 0<len(v)<=80 and not any(ord(c)<32 for c in v):result[section][key]=v
            elif key in ('font_size','bar_opacity'):
                if type(v) is int:result[section][key]=max(8 if key=='font_size' else 10,min(24 if key=='font_size' else 100,v))
            elif valid_color(v):result[section][key]=v.lower()
    return result

def appearance(settings,section):
    result=deepcopy(THEMES[section])
    if section=='graph' and valid_color(settings.get('accent')):result['accent']=settings['accent']
    result.update(clean_appearance(settings.get('appearance',{})).get(section,{}))
    return result

def contrast_ratio(a,b):
    def luminance(hex_color):
        rgb=[int(hex_color[i:i+2],16)/255 for i in (1,3,5)]
        rgb=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb]
        return sum(a*b for a,b in zip(rgb,(.2126,.7152,.0722)))
    x,y=sorted((luminance(a),luminance(b)))
    return (y+.05)/(x+.05)
