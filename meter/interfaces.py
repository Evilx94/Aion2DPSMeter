"""Choose the interface carrying AION traffic, never a hardcoded hardware GUID."""
from .language import tr as _tr
from threading import Lock
from scapy.all import conf,get_if_list,IP,TCP

def capture_interfaces():
    devices=[]
    for device in conf.ifaces.values():
        ip=str(getattr(device,'ip',''))
        if ip and not ip.startswith(('127.','169.254.')):
            name=str(device.network_name)
            if name not in devices:devices.append(name)
    if not devices:
        devices=[name for name in get_if_list() if 'loopback' not in name.lower()]
    if not devices:raise RuntimeError(_tr('Kein aktiver Netzwerkadapter gefunden. Npcap prüfen.'))
    return devices

class InterfaceSelector:
    def __init__(self):
        self.selected=None
        self.lock=Lock()
    def accepts(self,packet):
        if IP not in packet or TCP not in packet or 13328 not in (packet[TCP].sport,packet[TCP].dport):return False
        ip,tcp=packet[IP],packet[TCP]
        size=int(ip.len)-int(ip.ihl)*4-int(tcp.dataofs)*4
        interface=str(getattr(packet,'sniffed_on',''))
        with self.lock:
            if self.selected is None:
                if tcp.sport!=13328 or (size<=0 and not int(tcp.flags)&2):return False
                self.selected=interface
            return interface==self.selected
