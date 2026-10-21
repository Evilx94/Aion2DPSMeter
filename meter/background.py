"""Small Qt worker wrapper; callbacks are delivered on the UI thread."""
from PySide6.QtCore import QObject,Signal,QRunnable

class TaskSignals(QObject):
    ready=Signal(object)
    failed=Signal(str)

class Task(QRunnable):
    def __init__(self,function,*args,**kwargs):
        super().__init__();self.function=function;self.args=args;self.kwargs=kwargs;self.signals=TaskSignals()
    def run(self):
        try:self.signals.ready.emit(self.function(*self.args,**self.kwargs))
        except Exception as error:self.signals.failed.emit(str(error))
