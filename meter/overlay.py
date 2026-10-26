"""Compact painted DPS bars and timeline overlays. No game-process modification."""
from .language import tr as _tr,decimal
from PySide6.QtCore import Qt,QRectF,QPointF,QTimer,Signal,QEvent,QSize,QPoint
from PySide6.QtGui import QPainter,QColor,QPen,QFont,QPainterPath,QFontMetrics
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QApplication,QSizeGrip,QSizePolicy
from .game_window import GameWindowLocator
from .class_icons import action_icon
from .equipment import equipment_text
from .appearance import appearance,ACCESSIBLE_COLORS

CLASS_COLORS={'Gladiator':'#ed9766','Templar':'#6abde8','Assassin':'#bb8bea','Ranger':'#90c76e',
              'Sorcerer':'#8da7ff','Elementalist':'#65d2c3','Cleric':'#f3d77b','Chanter':'#f08da9','Brawler':'#ed6d7d'}
PALETTES={'Neon':['#65ebdf','#bd84ff','#ff7fa5','#ffd76b','#7fbbff'],
          'Pastell':['#98c9c1','#c5afde','#e2b4bc','#d8cfaa','#a9bddb']}

def color_for(actor,index,settings):
    palette=settings.get('palette','Klassenfarben')
    if palette=='Barrierearm':
        classes=list(CLASS_COLORS);slot=classes.index(actor.get('class')) if actor.get('class') in classes else index
        return ACCESSIBLE_COLORS[slot%len(ACCESSIBLE_COLORS)]
    if palette=='Einfarbig':return settings.get('accent','#71ddc4')
    if palette in PALETTES:return PALETTES[palette][index%len(PALETTES[palette])]
    return settings.get('class_colors',{}).get(actor.get('class',''),CLASS_COLORS.get(actor.get('class',''),'#86a8b8'))

def number(value):
    if value is None:return '—'
    if value>=1000000:return decimal(f'{value/1000000:.2f} M')
    if value>=1000:return decimal(f'{value/1000:.1f} k')
    return f'{value:.0f}'

def actor_label(actor,fight,report):
    if actor.get('provisional_membership'):
        return _tr('{0} · Entity {1} · ?',actor.get('name') or actor.get('class') or _tr('Spieler ?'),actor['id'])
    if actor.get('name'):return actor['name']
    previous=fight.get('self_identity',{});current=report.get('self_identity',{})
    own=previous.get('id',report.get('self_id'))
    # Presentation-only enrichment. Damage, membership and frozen logs stay intact.
    if (actor['id']==own and current.get('id')==own and current.get('confirmed')
            and current.get('source')=='server' and current.get('name')
            and previous.get('token') is not None and previous['token']==current.get('token')):
        return current['name']
    return _tr('Eigener Spieler') if actor['id']==own else _tr('Spieler {0}' ,actor['id'])

def timeline_points(fight,window=60,smoothing=5):
    values={item['second']:item['damage'] for item in fight.get('timeline',[]) if item['second']>=0}
    end=max(values,default=0)
    start=max(0,end-window+1)
    return [(second,sum(values.get(t,0) for t in range(max(0,second-smoothing+1),second+1))/min(smoothing,second+1))
            for second in range(start,end+1)]

def fight_title(fight):
    if not fight:return ''
    opponent=fight.get('boss_name') or fight.get('target_name')
    if not opponent:
        opponent=_tr('PvP-Kampf') if fight.get('combat_type')=='pvp' else (_tr('Gegner noch nicht erkannt') if fight.get('target_id') else _tr('Kampf'))
    area=fight.get('dungeon_name') or fight.get('region_name')
    title=f'{area} · {opponent}' if area else opponent
    if fight.get('damage_scope'):
        from .encounter_scope import scope_label
        title=scope_label(fight['damage_scope'])+' · '+title
    return title

NETWORK_TOOLTIP=('TCP: passive Hin-/Rücklaufzeit bis zur Server-Bestätigung eigener Daten '
                 '(Median der letzten 10 Sekunden; kann ACK-Verzögerung enthalten). '
                 'Kein ICMP- oder Spiel-Ping. Ohne frische Messung: —.\n'
                 'Paketverlust: aus diesem Mitschnitt nicht zuverlässig als Prozent messbar. '
                 'Lücken: vom Reassembler endgültig übersprungene Bereiche im Serverstream, '
                 'seit Meterstart. Möglich sind Netzwerkverlust oder fehlende Capture-Daten. '
                 'Fehlende Schadensmeldungen sind kein Nachweis für Paketverlust.')

def network_text(report):
    data=report.get('network',{});rtt=data.get('tcp_rtt_ms')
    ping=f'{rtt:.0f} ms' if isinstance(rtt,(int,float)) and rtt>=0 else '—'
    gaps=data.get('capture_gaps')
    return _tr('TCP {0} · Paketverlust — · Lücken {1}' ,ping,gaps if type(gaps) is int else '—')

class DamageView(QWidget):
    actorClicked=Signal(int)
    def __init__(self,graph=False,parent=None):
        super().__init__(parent)
        self.graph=graph
        self.report={'fights':[]}
        self.settings={}
        self.areas=[];self.scroll_index=0;self.paint_scale=1.0;self.theme=appearance({},'graph' if graph else 'dps')
        self.setMinimumSize(260,130)
    def set_data(self,report,settings):
        from .metrics import metric_report
        self.report,self.settings=metric_report(report,settings.get('display_metric','damage')),dict(settings)
        if not self.graph:
            from .unassigned_view import provisional_report
            self.report=provisional_report(self.report)
        self.theme=appearance(settings,'graph' if self.graph else 'dps');self.paint_scale=self.theme['font_size']/10
        self.setMinimumSize(round(260*self.paint_scale),round(130*self.paint_scale))
        title=fight_title(self.fight());self.encounter_title=title
        rate='HPS' if self.settings.get('display_metric','damage')!='damage' else 'DPS'
        self.setAccessibleName((rate+_tr('-Verlauf') if self.graph else rate)+' · '+title)
        self.setToolTip(title+'\n'+_tr(NETWORK_TOOLTIP))
        self.setAccessibleDescription(network_text(report)+'\n'+_tr(NETWORK_TOOLTIP))
        caption=getattr(self.window(),'caption',None)
        if caption is not None:
            f=self.fight() or {};caption.setText(f.get('boss_name') or f.get('target_name') or (rate+'-GRAPH' if self.graph else 'AION 2 · '+rate))
        self.update()
    def ui_font(self,size,weight=QFont.Weight.Normal):return QFont(self.theme['font_family'],size,weight)
    def fight(self):
        return self.report.get('fights',[])[-1] if self.report.get('fights') else None
    def paintEvent(self,event):
        painter=QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.scale(self.paint_scale,self.paint_scale)
        rect=QRectF(0,0,self.width()/self.paint_scale,self.height()/self.paint_scale).adjusted(4,4,-4,-4)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(self.theme['background']));painter.drawRoundedRect(QRectF(rect),8,8)
        painter.setFont(self.ui_font(8));painter.setPen(QColor(self.theme['secondary']))
        footer=QRectF(rect.left()+8,rect.bottom()-18,rect.width()-16,17)
        caption=QFontMetrics(painter.font()).elidedText(network_text(self.report),Qt.TextElideMode.ElideRight,int(footer.width()))
        painter.drawText(footer,Qt.AlignmentFlag.AlignVCenter|Qt.AlignmentFlag.AlignLeft,caption)
        rect=rect.adjusted(0,0,0,-21)
        painter.setPen(QColor(self.theme['secondary']));painter.setFont(self.ui_font(10))
        fight=self.fight()
        if not fight:
            painter.drawText(rect,Qt.AlignmentFlag.AlignCenter,_tr('Warte auf einen Kampf …'))
            return
        if fight.get('integrity','ok')!='ok':
            painter.setFont(self.ui_font(10,QFont.Weight.Bold));painter.setPen(QColor(self.theme['text']))
            title=QFontMetrics(painter.font()).elidedText(fight_title(fight),Qt.TextElideMode.ElideRight,max(0,int(rect.width()-24)))
            painter.drawText(QRectF(rect.left()+12,rect.top()+5,rect.width()-24,19),Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter,title)
            painter.setFont(self.ui_font(9));painter.setPen(QColor(self.theme['secondary']))
            painter.drawText(rect.adjusted(0,28,0,0),Qt.AlignmentFlag.AlignCenter,_tr('Daten unvollständig · keine verlässliche DPS'))
            return
        if self.graph:
            self.draw_graph(painter,rect,fight)
        else:
            self.draw_bars(painter,rect,fight)
    def draw_bars(self,painter,rect,fight):
        all_actors=fight.get('actors',[]);available=max(1,rect.height()-48)
        count=max(1,int(available//44));self.scroll_index=min(self.scroll_index,max(0,len(all_actors)-count))
        actors=all_actors[self.scroll_index:self.scroll_index+count];self.areas=[]
        title=fight_title(fight)
        seconds=int(fight.get('seconds',0));time=f'{seconds//60:02}:{seconds%60:02}'
        painter.setFont(self.ui_font(10,QFont.Weight.Bold));painter.setPen(QColor(self.theme['text']))
        label=QFontMetrics(painter.font()).elidedText(title,Qt.TextElideMode.ElideRight,max(0,int(rect.width()-82)))
        painter.drawText(rect.adjusted(12,5,-70,0),Qt.AlignmentFlag.AlignTop,label)
        painter.drawText(rect.adjusted(12,5,-12,0),Qt.AlignmentFlag.AlignTop|Qt.AlignmentFlag.AlignRight,time)
        unit=fight.get('metric_label',_tr('Schaden'))
        hint=number(fight.get('total_damage'))+' '+unit
        if fight.get('metric') and fight.get('healing_legacy'):hint+=_tr(' · älterer Log, Aufteilung ggf. unbekannt')
        if fight.get('partial'):hint+=_tr(' · Teilausschnitt')
        from .observation_quality import sparse_damage_coverage
        if sparse_damage_coverage(fight):hint=_tr('Direkter Gruppenschaden unvollständig · Anteile unbekannt')
        if self.report.get('group_state') in ('missing','invalid'):hint=_tr('Gruppendaten fehlen') if self.report['group_state']=='missing' else _tr('Gruppendaten unvollständig')
        if fight.get('tracking_scope')=='self':hint=_tr('World-/Abyssboss · nur eigener Spieler')+(_tr(' · Teilausschnitt') if fight.get('partial') else '')
        if fight.get('provisional_rows'):hint=_tr('Entity-Zeilen mit ? · Gruppe unbestätigt; separat erfasst')
        if len(all_actors)>len(actors):hint+=f' · {self.scroll_index+1}–{self.scroll_index+len(actors)}/{len(all_actors)}'
        painter.setFont(self.ui_font(8));painter.setPen(QColor(self.theme['secondary']))
        hint=QFontMetrics(painter.font()).elidedText(hint,Qt.TextElideMode.ElideRight,max(0,int(rect.width()-24)))
        painter.drawText(rect.adjusted(12,25,-12,0),Qt.AlignmentFlag.AlignTop,hint)
        hp=fight.get('target_hp');maximum_hp=fight.get('target_max_hp')
        if isinstance(hp,(int,float)) and isinstance(maximum_hp,(int,float)) and maximum_hp>0 and 0<=hp<=maximum_hp:
            painter.setPen(Qt.PenStyle.NoPen);painter.setBrush(QColor(self.theme['track']));painter.drawRoundedRect(QRectF(rect.left()+12,rect.top()+42,rect.width()-24,3),1,1)
            painter.setBrush(QColor(self.theme['health']));painter.drawRoundedRect(QRectF(rect.left()+12,rect.top()+42,(rect.width()-24)*hp/maximum_hp,3),1,1)
        row_height=min(52,available/max(1,len(actors)));maximum=max((a.get('damage',0) for a in all_actors),default=1) or 1
        own=fight.get('self_identity',{}).get('id',self.report.get('self_id'));total=fight.get('total_damage') or 0
        for index,actor in enumerate(actors):
            row=QRectF(rect.left()+8,rect.top()+48+index*row_height,rect.width()-16,row_height-4)
            shade=color_for(actor,index+self.scroll_index,self.settings);color=QColor(shade);color.setAlpha(round(255*self.theme['bar_opacity']/300))
            painter.setPen(Qt.PenStyle.NoPen);painter.setBrush(color);painter.drawRoundedRect(row,5,5)
            fill=QRectF(row);fill.setWidth(row.width()*max(0,actor.get('damage',0))/maximum);color.setAlpha(round(255*self.theme['bar_opacity']/100));painter.setBrush(color);painter.drawRoundedRect(fill,5,5)
            if actor['id']==own:painter.setPen(QPen(QColor(self.theme['border']),1));painter.setBrush(Qt.BrushStyle.NoBrush);painter.drawRoundedRect(row,5,5)
            label=actor_label(actor,fight,self.report)
            if actor.get('name_source') in ('manual','cache'):label+=' *'
            from .observation_quality import damage_amount_missing,damage_amount_partial,sparse_damage_coverage
            missing_amount=damage_amount_missing(actor,fight)
            partial_amount=damage_amount_partial(actor,fight)
            value=('—' if missing_amount else number(actor.get('dps'))+('*' if partial_amount else ''))+' /s';dps_font=self.ui_font(self.settings.get('dps_font_size',14),QFont.Weight.Bold)
            while dps_font.pointSize()>10 and QFontMetrics(dps_font).height()>row.height()-17:dps_font.setPointSize(dps_font.pointSize()-1)
            reserved=max(86,QFontMetrics(dps_font).horizontalAdvance(value)+14);left=row.left()+9
            painter.setFont(self.ui_font(9,QFont.Weight.DemiBold));painter.setPen(QColor(self.theme['bar_text']))
            name_rect=QRectF(left,row.top()+2,max(0,row.right()-reserved-left),row.height()-16)
            label=QFontMetrics(painter.font()).elidedText(label,Qt.TextElideMode.ElideRight,int(name_rect.width()));painter.drawText(name_rect,Qt.AlignmentFlag.AlignVCenter,label)
            painter.setFont(dps_font);painter.drawText(QRectF(row.right()-reserved,row.top(),reserved-8,row.height()-15),Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter,value)
            painter.setFont(self.ui_font(8));painter.setPen(QColor(self.theme['bar_detail']))
            share=100*actor.get('damage',0)/total if total else 0
            description=(actor.get('class') or _tr('Klasse unbekannt'))+' · '+number(actor.get('damage'))+' '+unit
            if missing_amount:description=(actor.get('class') or _tr('Klasse unbekannt'))+' · '+_tr('Kein Schaden erfasst')
            if partial_amount:description=(actor.get('class') or _tr('Klasse unbekannt'))+' · '+_tr('Nur periodischer Schaden erfasst')
            share_text='' if fight.get('tracking_scope')=='self' or fight.get('shares_unavailable') else '—' if missing_amount or sparse_damage_coverage(fight) else decimal(f'{share:.1f} %')
            description_width=max(0,row.right()-left-QFontMetrics(painter.font()).horizontalAdvance(share_text)-16)
            description=QFontMetrics(painter.font()).elidedText(description,Qt.TextElideMode.ElideRight,int(description_width))
            painter.drawText(QRectF(left,row.bottom()-17,description_width,15),Qt.AlignmentFlag.AlignLeft,description)
            painter.drawText(QRectF(left,row.bottom()-17,row.width()-(left-row.left())-8,15),Qt.AlignmentFlag.AlignRight,share_text)
            if not actor.get('provisional_membership'):self.areas.append((row,actor['id']))
        from .quality import quality_text
        self.setToolTip((_tr('Entity-Zeilen mit ? · Gruppe unbestätigt; separat erfasst')+'\n' if fight.get('provisional_rows') else '')+title+'\n'+'\n'.join(actor_label(a,fight,self.report)+' · '+(a.get('class') or _tr('Klasse unbekannt'))+' · '+equipment_text(a)+' · '+quality_text(a,fight) for a in actors)+_tr('\nSpieler anklicken: Fähigkeiten und Kampfanalyse. Mausrad: weitere Mitglieder. DPS und Anteile basieren auf dem beobachteten Kampf.\n')+_tr(NETWORK_TOOLTIP))
    def draw_graph(self,painter,rect,fight):
        painter.setPen(QColor(self.theme['text']))
        painter.setFont(self.ui_font(10,QFont.Weight.Bold))
        title=QFontMetrics(painter.font()).elidedText(fight_title(fight),Qt.TextElideMode.ElideRight,max(0,int(rect.width()-24)))
        painter.drawText(QRectF(rect.left()+12,rect.top()+5,rect.width()-24,19),Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter,title)
        painter.setFont(self.ui_font(8));painter.setPen(QColor(self.theme['secondary']))
        mode='HPS' if fight.get('metric') else 'DPS'
        painter.drawText(QRectF(rect.left()+12,rect.top()+25,rect.width()-24,16),Qt.AlignmentFlag.AlignLeft,mode+_tr('-VERLAUF · TEILWEISE') if fight.get('partial') else mode+_tr('-VERLAUF · 5-Sekunden-Mittel'))
        plot=QRectF(rect).adjusted(42,49,-14,-24)
        if not fight.get('timeline'):
            painter.drawText(plot,Qt.AlignmentFlag.AlignCenter,_tr('Noch keine Zeitreihe'))
            return
        points=timeline_points(fight)
        maximum=max((value for _,value in points),default=1) or 1
        painter.setFont(self.ui_font(8))
        for i in range(3):
            y=plot.bottom()-plot.height()*i/2
            painter.setPen(QPen(QColor(self.theme['grid']),1));painter.drawLine(QPointF(plot.left(),y),QPointF(plot.right(),y))
            painter.setPen(QColor(self.theme['secondary']));painter.drawText(QRectF(rect.left()+5,y-8,34,16),Qt.AlignmentFlag.AlignRight,number(maximum*i/2))
        path=QPainterPath()
        for index,(second,value) in enumerate(points):
            x=plot.left()+plot.width()*index/max(1,len(points)-1)
            y=plot.bottom()-plot.height()*value/maximum
            if index:path.lineTo(x,y)
            else:path.moveTo(x,y)
        painter.setPen(QPen(QColor(self.theme['accent']),2));painter.drawPath(path)
        painter.setPen(QColor(self.theme['secondary']))
        painter.drawText(QRectF(plot.left(),plot.bottom()+4,80,17),f'{points[0][0]} s')
        painter.drawText(QRectF(plot.right()-70,plot.bottom()+4,70,17),Qt.AlignmentFlag.AlignRight,f'{points[-1][0]} s')
    def wheelEvent(self,event):
        if not self.graph and event.angleDelta().y():
            self.scroll_index=max(0,self.scroll_index+(-1 if event.angleDelta().y()>0 else 1));self.update();event.accept()
        else:super().wheelEvent(event)
    def mousePressEvent(self,event):
        for rect,actor in self.areas:
            if rect.contains(event.position()/self.paint_scale):self.actorClicked.emit(actor);break

class OverlayWindow(QWidget):
    minimum_size=(280,180)
    resetRequested=Signal()
    optionsRequested=Signal()
    closed=Signal()
    positionChanged=Signal(object)
    freePositionChanged=Signal(object)
    sizeChanged=Signal(object)
    lockChanged=Signal(bool)
    def __init__(self,graph=False,locator=None):
        flags=Qt.WindowType.Tool|Qt.WindowType.FramelessWindowHint|Qt.WindowType.WindowStaysOnTopHint|Qt.WindowType.WindowDoesNotAcceptFocus
        super().__init__(None,flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setWindowTitle(_tr('AION 2 · Graph-Overlay') if graph else _tr('AION 2 · DPS-Overlay'))
        self.graph=graph;self.attached=False;self.wanted=False;self.locked=False
        self.drag_offset=None;self.anchor_offset=None;self.free_position=None;self.applying=True;self.resizing=False
        self.locator=locator or GameWindowLocator();self.last_saved_size=None
        self.geometry_timer=QTimer(self);self.geometry_timer.setSingleShot(True);self.geometry_timer.setInterval(250);self.geometry_timer.timeout.connect(self.commit_size)
        layout=QVBoxLayout(self);layout.setContentsMargins(5,5,5,5);layout.setSpacing(3)
        bar=QHBoxLayout();bar.setSpacing(3)
        self.caption=QLabel('DPS-GRAPH' if graph else 'AION 2 · DPS')
        self.caption.setStyleSheet('color:#d8e7ee;background:#132029;padding:6px;font-weight:600;')
        self.caption.setMinimumWidth(0);self.caption.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        self.caption.installEventFilter(self);bar.addWidget(self.caption,1)
        reset=QPushButton();reset.setIcon(action_icon('reset'));reset.setStyleSheet('background:#263c48;border:0;padding:3px;');reset.setFixedWidth(24);reset.setToolTip(_tr('Neuen Kampf beginnen (Logs bleiben erhalten)'));reset.clicked.connect(self.resetRequested.emit);bar.addWidget(reset)
        reset.setObjectName('resetEncounter')
        options=QPushButton();options.setIcon(action_icon('options'));options.setStyleSheet('background:#263c48;border:0;padding:3px;');options.setFixedWidth(24);options.setToolTip(_tr('Overlay-Optionen'));options.clicked.connect(self.optionsRequested.emit);bar.addWidget(options)
        options.setObjectName('overlayOptions')
        self.lock_button=QPushButton(_tr('Fixieren'));self.lock_button.setCheckable(True);self.lock_button.setFixedWidth(72)
        self.lock_button.setStyleSheet('background:#263c48;color:white;border:0;padding:5px;')
        self.lock_button.toggled.connect(self.set_locked);bar.addWidget(self.lock_button)
        close=QPushButton('×');close.setFixedWidth(25);close.clicked.connect(self.request_close)
        close.setStyleSheet('background:#263c48;color:white;border:0;');bar.addWidget(close)
        layout.addLayout(bar);self.view=DamageView(graph);layout.addWidget(self.view)
        self.size_grip=QSizeGrip(self);self.size_grip.setFixedSize(16,16);self.size_grip.setToolTip(_tr('Größe ändern'));self.size_grip.installEventFilter(self)
        self.setMinimumSize(*self.minimum_size);self.setMaximumSize(2400,1600);self.resize(350,220 if graph else 260)
        screen=QApplication.primaryScreen()
        if screen:
            available=screen.availableGeometry();self.move(available.right()-self.width()-18,available.bottom()-self.height()-18 if graph else available.top()+70)
        self.free_position=(self.x(),self.y());self.last_saved_size=(self.width(),self.height());self.applying=False
        self.timer=QTimer(self);self.timer.setInterval(350);self.timer.timeout.connect(self.follow_game);self.timer.start()
    @staticmethod
    def pair(value):
        import math
        return len(value)==2 and all(type(v) in (int,float) and math.isfinite(v) for v in value)
    def visible_position(self,position,size=None):
        point=QPoint(round(position[0]),round(position[1]));screens=QApplication.screens()
        if not screens:return point
        screen=next((screen for screen in screens if screen.availableGeometry().contains(point)),QApplication.primaryScreen())
        rect=screen.availableGeometry();size=size or self.size()
        return QPoint(max(rect.left(),min(point.x(),rect.right()-min(size.width(),rect.width())+1)),max(rect.top(),min(point.y(),rect.bottom()-min(size.height(),rect.height())+1)))
    def request_close(self):
        self.commit_size();self.wanted=False;self.hide();self.geometry_timer.stop();self.closed.emit()
    def set_locked(self,locked,emit=True):
        self.locked=bool(locked);self.drag_offset=None;self.resizing=False
        if self.locked:self.commit_size();self.setFixedSize(self.size())
        else:self.setMinimumSize(*self.minimum_size);self.setMaximumSize(2400,1600)
        self.lock_button.blockSignals(True);self.lock_button.setChecked(self.locked);self.lock_button.setText(_tr('Lösen') if self.locked else _tr('Fixieren'));self.lock_button.blockSignals(False)
        self.caption.setCursor(Qt.CursorShape.ArrowCursor if self.locked else Qt.CursorShape.SizeAllCursor)
        self.caption.setToolTip(_tr('Position und Größe fixiert. Mit „Lösen“ wieder einstellen.') if self.locked else _tr('Am Titel ziehen – auch am Spielfenster angeheftet.'))
        self.size_grip.setVisible(not self.locked);self.size_grip.raise_()
        if emit:self.lockChanged.emit(self.locked)
    def configure(self,settings,wanted):
        self.applying=True;self.geometry_timer.stop();prefix='graph' if self.graph else 'dps'
        theme=appearance(settings,settings.get('_appearance_section',prefix))
        scale=max(1,theme['font_size']/10);base=type(self).minimum_size
        self.minimum_size=(round(base[0]*scale),round(base[1]*scale))
        attached=bool(settings.get('attached',False))
        if attached and not self.attached:
            self.free_position=(self.x(),self.y());self.freePositionChanged.emit(list(self.free_position))
        self.attached=attached;self.wanted=wanted
        saved=settings.get(prefix+'_position',[])
        if self.pair(saved):self.anchor_offset=tuple(saved)
        free=settings.get(prefix+'_free_position',[])
        if self.pair(free):self.free_position=tuple(free)
        size=settings.get(prefix+'_size',[350,220 if self.graph else 260])
        self.set_locked(False,False)
        if self.pair(size):self.resize(max(self.minimum_size[0],min(2400,round(size[0]))),max(self.minimum_size[1],min(1600,round(size[1]))))
        family=theme['font_family'];font=QFont(family,theme['font_size']);metrics=QFontMetrics(font)
        self.caption.setFont(font)
        self.caption.setStyleSheet(f"color:{theme['text']};background:{theme['header']};padding:6px;font-weight:600;")
        for button in self.findChildren(QPushButton):
            if button.objectName() in ('resetEncounter','overlayOptions'):button.setIcon(action_icon('reset' if button.objectName()=='resetEncounter' else 'options',theme['control_text']))
            button.setFont(font);button.setStyleSheet(f"background:{theme['controls']};color:{theme['control_text']};border:1px solid {theme['secondary']};padding:4px;")
            if button is self.lock_button:button.setFixedWidth(max(72,max(metrics.horizontalAdvance(label) for label in ('Lock','Unlock','Fixieren','Lösen'))+18))
            elif button.text()=='×':button.setFixedWidth(max(25,metrics.horizontalAdvance('×')+12))
            else:button.setFixedWidth(max(24,round(24*scale)))
        self.setWindowOpacity(settings.get('opacity',88)/100)
        flag=Qt.WindowType.WindowTransparentForInput;click=settings.get('click_through',False)
        if bool(self.windowFlags()&flag)!=click:self.setWindowFlag(flag,click)
        if not attached and self.free_position:self.move(self.visible_position(self.free_position))
        self.set_locked(settings.get(prefix+'_locked',False),False)
        self.last_saved_size=(self.width(),self.height());self.applying=False
        if wanted:self.follow_game()
        else:self.hide()
    def follow_game(self):
        if not self.wanted:return
        if not self.attached:
            self.show();return
        rect=self.locator.find()
        if rect is None:
            self.caption.setText(_tr('Warte auf AION 2'));self.hide();return
        if not rect.visible or not rect.foreground:self.hide();return
        self.caption.setText('DPS-GRAPH · AION 2' if self.graph else 'DPS · AION 2')
        x,y,width,height=self.game_geometry(rect)
        dx,dy=self.anchor_offset or (width-self.width()-18,height-self.height()-18 if self.graph else 45)
        dx=max(0,min(dx,max(0,width-self.width())));dy=max(0,min(dy,max(0,height-self.height())))
        if not self.resizing:self.move(round(x+dx),round(y+dy))
        self.show()
    def game_geometry(self,rect):
        screen=next((s for s in QApplication.screens() if s.name()==rect.monitor),QApplication.primaryScreen())
        scale=screen.devicePixelRatio() if screen else 1;origin=screen.geometry().topLeft() if screen else QPointF(0,0)
        return origin.x()+(rect.x-rect.monitor_x)/scale,origin.y()+(rect.y-rect.monitor_y)/scale,rect.width/scale,rect.height/scale
    def eventFilter(self,watched,event):
        if watched is getattr(self,'size_grip',None):
            if event.type()==QEvent.Type.MouseButtonPress:self.resizing=not self.locked
            elif event.type()==QEvent.Type.MouseButtonRelease:self.resizing=False;self.commit_size();self.follow_game()
        if watched is self.caption:
            if event.type()==QEvent.Type.MouseButtonPress:self.mousePressEvent(event);return True
            if event.type()==QEvent.Type.MouseMove:self.mouseMoveEvent(event);return True
            if event.type()==QEvent.Type.MouseButtonRelease:self.mouseReleaseEvent(event);return True
        return super().eventFilter(watched,event)
    def mousePressEvent(self,event):
        if not self.locked and event.button()==Qt.MouseButton.LeftButton:self.drag_offset=event.globalPosition().toPoint()-self.pos()
    def mouseMoveEvent(self,event):
        if self.locked or self.drag_offset is None:return
        target=event.globalPosition().toPoint()-self.drag_offset
        if self.attached:
            rect=self.locator.find()
            if rect is None:return
            x,y,width,height=self.game_geometry(rect)
            self.anchor_offset=(max(0,min(target.x()-x,max(0,width-self.width()))),max(0,min(target.y()-y,max(0,height-self.height()))));self.follow_game()
        else:self.move(target)
    def mouseReleaseEvent(self,event):
        if not self.locked and self.drag_offset is not None:
            if self.attached and self.anchor_offset is not None:self.positionChanged.emit(list(self.anchor_offset))
            elif not self.attached:self.free_position=(self.x(),self.y());self.freePositionChanged.emit(list(self.free_position))
        self.drag_offset=None
    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,'size_grip'):self.size_grip.move(self.width()-19,self.height()-19);self.size_grip.raise_()
        if hasattr(self,'geometry_timer') and not self.applying and self.wanted:self.geometry_timer.start()
    def commit_size(self):
        if self.applying:return
        size=(self.width(),self.height())
        if size!=self.last_saved_size:self.last_saved_size=size;self.sizeChanged.emit(list(size))
    def closeEvent(self,event):self.request_close();event.ignore()
