"""Per-process diagnostics for pythonw, including GUI hangs and worker failures."""
from pathlib import Path
from datetime import datetime
import sys,logging,faulthandler,threading,time,traceback,os
_HANDLE=None
_LOGGER=logging.getLogger('aion2')

_LOCK=threading.RLock()
_LOGGER.propagate=False

def setup(base):
    with _LOCK:
        if _HANDLE:return _HANDLE.name
        return set_enabled(True,Path(base)/'reports')

def set_enabled(enabled,directory):
    global _HANDLE
    with _LOCK:
        if enabled and _HANDLE:return _HANDLE.name
        faulthandler.disable()
        for handler in list(_LOGGER.handlers):
            _LOGGER.removeHandler(handler);handler.close()
        if _HANDLE:
            _HANDLE.close();_HANDLE=None
        _LOGGER.setLevel(logging.INFO)
        if enabled:
            folder=Path(directory)/'logs';folder.mkdir(parents=True,exist_ok=True)
            path=folder/f'meter_{datetime.now():%Y%m%d_%H%M%S_%f}_{os.getpid()}.log'
            _HANDLE=path.open('a',encoding='utf-8',buffering=1)
            handler=logging.StreamHandler(_HANDLE)
            handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
            _LOGGER.addHandler(handler);faulthandler.enable(file=_HANDLE,all_threads=True)
        else:_LOGGER.addHandler(logging.NullHandler())
        def exception(kind,value,tb):
            _LOGGER.error('Unhandled exception',exc_info=(kind,value,tb))
        sys.excepthook=exception
        threading.excepthook=lambda args:exception(args.exc_type,args.exc_value,args.exc_traceback)
        _LOGGER.info('Startup pid=%s Python=%s',os.getpid(),sys.version)
        return _HANDLE.name if _HANDLE else None

def info(message,*args):
    _LOGGER.info(message,*args)

def error(message):
    _LOGGER.exception(message)

class GuiWatchdog:
    def __init__(self, threshold=8):
        self.last=time.monotonic()
        self.threshold=threshold
        self.stop=threading.Event()
        self.thread=threading.Thread(target=self.run,name='GUI-watchdog',daemon=True)
        self.thread.start()
    def beat(self):
        self.last=time.monotonic()
    def run(self):
        reported=False
        while not self.stop.wait(1):
            elapsed=time.monotonic()-self.last
            if elapsed>self.threshold and not reported:
                _LOGGER.error('GUI heartbeat missing for %.1fs',elapsed)
                with _LOCK:
                    if _HANDLE:faulthandler.dump_traceback(file=_HANDLE,all_threads=True)
                reported=True
            elif elapsed<=self.threshold:
                reported=False
