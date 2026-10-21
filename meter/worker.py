"""Scapy/Npcap worker for the separate meter; no Analyzer imports."""
from .language import tr as _tr
from pathlib import Path
from threading import Event,RLock
from uuid import uuid4
import time
from PySide6.QtCore import QThread,Signal
from scapy.all import AsyncSniffer
from .core.session import Session
from .core.skill_labels import SkillLabels
from .core.npc_policy import NpcPolicy
from .core.encounters import EncounterCatalog
from .core.scapy_capture import segment,observation
from .core.binary import InvalidData
from .interfaces import capture_interfaces,InterfaceSelector
from . import diagnostics
from .preferences import runtime_directory,Preferences
from .combat_logs import CombatLogWriter
from .recording import PacketRecorder
BASE=Path(__file__).resolve().parent.parent
class LockedSession:
    def __init__(self,preferred_identity=None,track_pvp=True,skill_labels=None,npc_policy=None,encounters=None):self.core=Session(preferred_identity=preferred_identity,track_pvp=track_pvp,skill_labels=skill_labels,npc_policy=npc_policy,encounters=encounters);self.lock=RLock()
    def packet(self,packet):
        with self.lock:
            self.core.packet(segment(packet))
            self.core.network.observe(observation(packet))
    def snapshot(self):
        with self.lock:return self.core.snapshot(now_ms=int(time.time()*1000))
    def manual_self_name(self,actor,name):
        with self.lock:self.core.manual_self_name(actor,name)
    def tick(self):
        with self.lock:
            now=max(int(time.time()*1000),self.core.ledger.time)
            stream=self.core.stream
            # Pending bytes retain their captured delivery time. Idle ticks must
            # not overtake them, including while waiting for reordered bytes.
            if stream and stream.pending:
                oldest=min(at for _,at in stream.pending.values())
                if now-oldest>1500:
                    stream.flush_gap()
                    if stream.pending:oldest=min(at for _,at in stream.pending.values())
                if stream.pending:now=min(now,oldest)
            self.core.ledger.tick(max(now,self.core.ledger.time))
    def finish(self):
        with self.lock:self.core.ledger.finish('stop')
class MeterWorker(QThread):
    failed=Signal(str);status=Signal(str)
    def __init__(self,mode='live',source='auto',record=False,data_dir=None):
        super().__init__()
        if mode!='live':raise ValueError(_tr('Dieses Projekt startet ausschließlich Live-Capture.'))
        self.cancel=Event();self.data_dir=Path(data_dir) if data_dir else runtime_directory();self.record=record
        settings=Preferences(self.data_dir).values
        self.session=LockedSession(settings['character_identity'],settings['track_pvp'],SkillLabels.for_runtime(self.data_dir,settings),NpcPolicy.for_runtime(self.data_dir),EncounterCatalog.for_runtime(self.data_dir))
        self.recorder=PacketRecorder(self.data_dir/'captures',record)
        self.save_combat=settings['save_combat'];self.log_writer=CombatLogWriter(settings['log_folder'] or self.data_dir/'sessions');self.log_error='';self.revision=0;self.interface=None;self.started_ms=int(time.time()*1000)
        self.source=source;self.last_report=None;self.session_id=uuid4().hex;self.snapshot_lock=RLock();self.failure=None
    def set_recording(self,enabled):
        self.record=bool(enabled);self.recorder.set_enabled(enabled)
    def set_logging(self,enabled,directory):
        with self.snapshot_lock:
            self.save_combat=bool(enabled)
            if self.log_writer.directory!=Path(directory):self.log_writer=CombatLogWriter(directory)
    def emit_snapshot(self,force=False):
        with self.snapshot_lock:
            self.revision+=1;recording=self.recorder.snapshot()
            report=self.session.snapshot();report['session']={'id':self.session_id,'mode':'live','source':'auto','revision':self.revision,'started_ms':self.started_ms,'interface':self.interface,'recording':recording['current'],'recordings':recording['files']}
            if self.save_combat:
                try:self.log_writer.save(report,force);self.log_error=''
                except (OSError,ValueError) as error:self.log_error=str(error);diagnostics.error('Combat log write failed')
            report['storage']={'combat_enabled':self.save_combat,'combat_folder':str(self.log_writer.directory),'combat_latest':str(self.log_writer.last_path) if self.log_writer.last_path else None,'combat_error':self.log_error,'packet_folder':str(self.recorder.directory),'packet_enabled':recording['enabled'],'packet_error':recording['error'],'config':str(self.data_dir/'preferences.json')}
            self.last_report=report
    def run(self):
        sniffer=None;selector=InterfaceSelector()
        try:
            def receive(packet):
                if self.cancel.is_set() or not selector.accepts(packet):return
                try:
                    self.interface=selector.selected
                    try:self.recorder.write(packet)
                    except OSError as error:
                        self.recorder.error=str(error);self.recorder.close();diagnostics.error('Packet recording write failed')
                    self.session.packet(packet)
                except InvalidData:
                    with self.session.lock:self.session.core.loss()
                except Exception as error:self.failure=str(error);self.cancel.set()
            sniffer=AsyncSniffer(iface=capture_interfaces(),filter='tcp port 13328',prn=receive,store=False)
            sniffer.start();self.status.emit(_tr('Live: wartet auf AION-2-Serverdaten (TCP 13328)'))
            next_report=0
            while not self.cancel.wait(.1):
                if sniffer.exception:raise sniffer.exception
                self.session.tick()
                if time.monotonic()>=next_report:self.emit_snapshot();next_report=time.monotonic()+.5
            if self.failure:raise RuntimeError(self.failure)
        except Exception as error:
            self.failure=str(error);diagnostics.error(_tr('Live worker failed'));self.failed.emit(self.failure)
        finally:
            try:
                if sniffer and sniffer.running:sniffer.stop()
            finally:
                try:self.recorder.close()
                except OSError as error:self.recorder.error=str(error)
                finally:self.session.finish();self.emit_snapshot(True)
