"""Entry point for the separate live meter."""
import sys
from PySide6.QtWidgets import QApplication
from .dashboard import LiveDashboard
from .preferences import runtime_directory,Preferences
from . import diagnostics

def main():
    directory=runtime_directory();preferences=Preferences(directory)
    diagnostics.set_enabled(preferences.values['save_debug'],directory)
    from PySide6.QtCore import QTimer
    app=QApplication(sys.argv[:1]);watchdog=diagnostics.GuiWatchdog()
    heartbeat=QTimer(app);heartbeat.setInterval(250);heartbeat.timeout.connect(watchdog.beat);heartbeat.start()
    app.aboutToQuit.connect(watchdog.stop.set)
    window=LiveDashboard(data_dir=directory);window.show()
    try:return app.exec()
    finally:
        # Release parentless overlay windows while QApplication still exists;
        # native Qt destruction during Python shutdown can race their callbacks.
        from PySide6.QtCore import QCoreApplication,QEvent
        heartbeat.stop();watchdog.stop.set()
        for overlay in (window.overlay,window.graph_overlay):
            overlay.timer.stop();overlay.hide();overlay.deleteLater()
        window.timer.stop();window.hide();window.deleteLater()
        QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
if __name__=='__main__':raise SystemExit(main())
