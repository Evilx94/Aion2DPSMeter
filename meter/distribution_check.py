"""Packaged runtime self-test, explicitly requested with --self-test PATH.

No access to existing logs/preferences. Capture probing counts packets only;
it never records traffic or writes packet contents.
"""
from pathlib import Path
import sys,json,os,time,ctypes,traceback

def run(destination,capture=False):
    output=Path(destination).resolve();output.parent.mkdir(parents=True,exist_ok=True)
    user=output.parent/('userdata-'+output.stem)
    os.environ['AION2_METER_DATA_DIR']=str(user)
    report={'checks':{},'frozen':bool(getattr(sys,'frozen',False))}
    window=None;app=None
    try:
        from . import __version__
        import scapy,PySide6
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QCoreApplication,QEvent
        app=QApplication.instance() or QApplication([])
        report.update(version=__version__,python=sys.version,executable=sys.executable)
        bundle=Path(getattr(sys,'_MEIPASS',Path(__file__).parent.parent)).resolve()
        report['bundle']=str(bundle)
        report['module_files']={name:str(Path(module.__file__).resolve()) for name,module in [('scapy',scapy),('PySide6',PySide6)]}
        if report['frozen']:
            assert all(Path(p).is_relative_to(bundle) for p in report['module_files'].values())
            kernel=ctypes.WinDLL('kernel32',use_last_error=True)
            kernel.GetModuleHandleW.argtypes=[ctypes.c_wchar_p];kernel.GetModuleHandleW.restype=ctypes.c_void_p
            kernel.GetModuleFileNameW.argtypes=[ctypes.c_void_p,ctypes.c_wchar_p,ctypes.c_uint];kernel.GetModuleFileNameW.restype=ctypes.c_uint
            dlls={}
            for name in ('python315.dll','Qt6Core.dll'):
                handle=kernel.GetModuleHandleW(name);assert handle,name
                text=ctypes.create_unicode_buffer(32768);assert kernel.GetModuleFileNameW(handle,text,len(text))
                dlls[name]=text.value;assert Path(text.value).resolve().is_relative_to(bundle),text.value
            report['loaded_dlls']=dlls
        report['checks']['bundled_runtime']=True
        from .catalog_store import document
        for filename,section in [('skill_labels.json','records'),('npc_labels.json','facts'),('dungeon_labels.json','maps'),('buff_labels.json','records'),('periodic_skills.json','facts')]:assert document(filename)[section]
        from .pets import catalog
        report['checks']['catalogs']=True
        from .core.binary import raw_lz4
        assert raw_lz4(b'\x50hello',5)==b'hello';report['checks']['lz4']=True
        from .core.session import Session
        from .core.damage import Hit
        session=Session();session.ledger.world.identity(1,'Test',2313,True,class_name='Cleric');session.ledger.accept(1000,Hit(1,99,17010000,100))
        assert session.snapshot()['fights'][0]['total_damage']==100;report['checks']['combat']=True
        from .events import schedule,reset_events
        from datetime import datetime
        now=int(datetime.fromisoformat('2026-10-25T06:59:00+00:00').timestamp())
        assert schedule(reset_events()[:1],now,'Europe/Berlin')[0]['remaining']==60;report['checks']['clock']=True
        from .dashboard import LiveDashboard
        window=LiveDashboard(False,user);window.resize(700,740);window.show();app.processEvents()
        assert __version__ in window.windowTitle();window.latest=session.snapshot();window.render();app.processEvents()
        assert not window.grab().isNull();report['checks']['gui']=True
        from .update_dialog import UpdateDialog
        dialog=UpdateDialog(user,window.settings,parent=window);assert dialog.job is None;dialog.close();report['checks']['update_dialog']=True
        report['capture_requested']=bool(capture)
        if capture:
            from .interfaces import capture_interfaces
            devices=capture_interfaces();report['capture_interfaces']=len(devices)
            assert devices, "No capture interface available"
            from scapy.all import AsyncSniffer,conf
            counts=[0]
            def count(packet):counts[0]+=1
            sniffer=AsyncSniffer(iface=devices,filter='tcp port 13328',store=False,prn=count)
            sniffer.start();time.sleep(2);sniffer.stop()
            report.update(capture_packets=counts[0],capture_backend_pcap=bool(conf.use_pcap));report['checks']['capture']=True
        report['ok']=True
    except Exception:
        report['ok']=False;report['error']=traceback.format_exc()
    finally:
        if window:
            window.close()
            for overlay in (window.overlay,window.graph_overlay,window.event_overlay):overlay.deleteLater()
            window.deleteLater()
        if app:
            from PySide6.QtCore import QCoreApplication,QEvent
            QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);app.processEvents()
        from . import diagnostics
        diagnostics.set_enabled(False,user)
        output.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    return 0 if report.get('ok') else 1
