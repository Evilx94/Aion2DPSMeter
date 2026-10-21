"""Painted action icons and optional user-supplied skill images."""
from PySide6.QtCore import QRectF,QPointF,Qt
from PySide6.QtGui import QPixmap,QPainter,QColor,QIcon,QPen,QPainterPath

from .preferences import runtime_directory
_external={}

def external_pixmap(category,name,size):
    folder=runtime_directory()/'assets'/category
    for suffix in ('.png','.webp'):
        path=folder/(str(name)+suffix)
        try:
            stat=path.stat()
            if stat.st_size>8*1024*1024:continue
        except OSError:continue
        key=(str(path),stat.st_mtime_ns,stat.st_size,size)
        if key in _external:return _external[key]
        picture=QPixmap(str(path))
        if picture.isNull():continue
        picture=picture.scaled(size*2,size*2,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation);picture.setDevicePixelRatio(2)
        canvas=QPixmap(size*2,size*2);canvas.setDevicePixelRatio(2);canvas.fill(QColor('transparent'));p=QPainter(canvas);p.drawPixmap(int((size-picture.width()/2)/2),int((size-picture.height()/2)/2),picture);p.end()
        if len(_external)>128:_external.clear()
        _external[key]=canvas;return canvas
    return None

def skill_icon(skill,size=20):
    picture=external_pixmap('skills',skill,size)
    return QIcon(picture) if picture is not None else QIcon()

def action_icon(kind,color='#dce9f2'):
    canvas=QPixmap(40,40);canvas.setDevicePixelRatio(2);canvas.fill(QColor('transparent'));p=QPainter(canvas);p.setRenderHint(QPainter.RenderHint.Antialiasing);p.setPen(QPen(QColor(color),1.8))
    if kind=='reset':
        p.drawArc(QRectF(4,4,12,12),40*16,280*16);path=QPainterPath();path.moveTo(15,3);path.lineTo(15,8);path.lineTo(10,7);p.drawPath(path)
    else:
        import math
        p.drawEllipse(QRectF(5,5,10,10));p.drawEllipse(QRectF(8,8,4,4))
        for i in range(8):
            a=i*math.pi/4;p.drawLine(QPointF(10+5*math.cos(a),10+5*math.sin(a)),QPointF(10+8*math.cos(a),10+8*math.sin(a)))
    p.end();return QIcon(canvas)
