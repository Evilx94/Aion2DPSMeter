"""Read-only AION client-window bounds for a separate Qt overlay; no injection."""
from dataclasses import dataclass
import os

@dataclass(frozen=True)
class GameRect:
    x:int;y:int;width:int;height:int
    visible:bool=True
    foreground:bool=True
    monitor:str=''
    monitor_x:int=0
    monitor_y:int=0

class GameWindowLocator:
    names={'aion2.exe','aion2-win64-shipping.exe'}
    def __init__(self):
        self.available=os.name=='nt'
    def find(self):
        if not self.available:return None
        import ctypes
        from ctypes import wintypes as w
        user=ctypes.WinDLL('user32',use_last_error=True)
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        user.IsWindowVisible.argtypes=[w.HWND];user.IsWindowVisible.restype=w.BOOL
        user.IsIconic.argtypes=[w.HWND];user.IsIconic.restype=w.BOOL
        user.GetForegroundWindow.restype=w.HWND
        user.GetWindowThreadProcessId.argtypes=[w.HWND,ctypes.POINTER(w.DWORD)]
        user.GetClientRect.argtypes=[w.HWND,ctypes.POINTER(w.RECT)]
        user.ClientToScreen.argtypes=[w.HWND,ctypes.POINTER(w.POINT)]
        kernel.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];kernel.OpenProcess.restype=w.HANDLE
        kernel.QueryFullProcessImageNameW.argtypes=[w.HANDLE,w.DWORD,w.LPWSTR,ctypes.POINTER(w.DWORD)]
        kernel.CloseHandle.argtypes=[w.HANDLE]
        callback_type=ctypes.WINFUNCTYPE(w.BOOL,w.HWND,w.LPARAM)
        user.EnumWindows.argtypes=[callback_type,w.LPARAM]
        matches=[]
        def visit(hwnd,param):
            if not user.IsWindowVisible(hwnd):return True
            pid=w.DWORD();user.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
            if pid.value==os.getpid():return True
            handle=kernel.OpenProcess(0x1000,False,pid.value)
            if not handle:return True
            try:
                text=ctypes.create_unicode_buffer(32768);size=w.DWORD(len(text))
                if not kernel.QueryFullProcessImageNameW(handle,0,text,ctypes.byref(size)):return True
                if text.value.rsplit('\\',1)[-1].lower() not in self.names:return True
                rect=w.RECT();point=w.POINT(0,0)
                if not user.GetClientRect(hwnd,ctypes.byref(rect)) or not user.ClientToScreen(hwnd,ctypes.byref(point)):return True
                if rect.right<100 or rect.bottom<100:return True
                class MONITORINFOEX(ctypes.Structure):
                    _fields_=[('cbSize',w.DWORD),('rcMonitor',w.RECT),('rcWork',w.RECT),('dwFlags',w.DWORD),('szDevice',w.WCHAR*32)]
                user.MonitorFromWindow.argtypes=[w.HWND,w.DWORD];user.MonitorFromWindow.restype=w.HANDLE
                user.GetMonitorInfoW.argtypes=[w.HANDLE,ctypes.POINTER(MONITORINFOEX)]
                monitor=MONITORINFOEX();monitor.cbSize=ctypes.sizeof(monitor)
                user.GetMonitorInfoW(user.MonitorFromWindow(hwnd,2),ctypes.byref(monitor))
                matches.append(GameRect(point.x,point.y,rect.right,rect.bottom,
                    not bool(user.IsIconic(hwnd)),user.GetForegroundWindow()==hwnd,
                    monitor.szDevice,monitor.rcMonitor.left,monitor.rcMonitor.top))
            finally:kernel.CloseHandle(handle)
            return True
        callback=callback_type(visit)
        user.EnumWindows(callback,0)
        return next((rect for rect in matches if rect.foreground),matches[0] if matches else None)
