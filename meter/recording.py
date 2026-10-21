"""Thread-safe packet recording that can be enabled while capture continues."""
from pathlib import Path
from threading import RLock
from datetime import datetime
from uuid import uuid4
from scapy.all import PcapWriter

class PacketRecorder:
    def __init__(self,directory,enabled=False):
        self.directory=Path(directory);self.enabled=enabled;self.writer=None;self.paths=[];self.lock=RLock();self.error=''
    def set_enabled(self,enabled):
        with self.lock:
            self.enabled=bool(enabled)
            if not self.enabled and self.writer:self.writer.close();self.writer=None
            if self.enabled:self.error=''
    def write(self,packet):
        with self.lock:
            if not self.enabled:return
            if self.writer is None:
                self.directory.mkdir(parents=True,exist_ok=True)
                path=self.directory/f'live_{datetime.now():%Y%m%d_%H%M%S_%f}_{uuid4().hex[:6]}.pcap'
                self.writer=PcapWriter(str(path),sync=True);self.paths.append(str(path))
            self.writer.write(packet)
    def snapshot(self):
        with self.lock:return {'enabled':self.enabled,'files':list(self.paths),'current':self.paths[-1] if self.paths else None,'error':self.error}
    def close(self):self.set_enabled(False)
