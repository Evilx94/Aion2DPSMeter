"""Build a portable Windows folder using existing Python + PyInstaller.

No installs or security-setting changes. Use a fresh output and work folder.
"""
from pathlib import Path
import argparse,ast,hashlib,importlib.metadata as metadata,json,os,shutil,subprocess,sys,urllib.request,zipfile

def version_of(source):
    tree=ast.parse((source/'meter/__init__.py').read_text(encoding='utf-8'))
    return next(n.value.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='__version__' for t in n.targets))

def version_resource(version):
    import re
    match=re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:-[0-9A-Za-z.-]+)?",version)
    if not match:raise ValueError('Invalid release version')
    numbers=tuple(map(int,match.groups()))+(0,)
    if any(n>65535 for n in numbers):raise ValueError('Version component exceeds PE limit')
    fields={'FileDescription':'Aion2Meter','FileVersion':version,'ProductName':'Aion2Meter','ProductVersion':version,'OriginalFilename':'Aion2Meter.exe'}
    entries=','.join('StringStruct('+repr(k)+','+repr(v)+')' for k,v in fields.items())
    return "VSVersionInfo(ffi=FixedFileInfo(filevers="+repr(numbers)+",prodvers="+repr(numbers)+",mask=0x3f,flags=0,OS=0x40004,fileType=1,subtype=0,date=(0,0)),kids=[StringFileInfo([StringTable('040904B0',["+entries+"])]),VarFileInfo([VarStruct('Translation',[1033,1200])])])"


def checksum_zip(folder):
    records=[{'path':p.relative_to(folder).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(folder.rglob('*')) if p.is_file() and p.name!='SOURCE-MANIFEST.json']
    (folder/'SOURCE-MANIFEST.json').write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8')
    archive=folder.parent/(folder.name+'.zip');temporary=archive.with_suffix('.tmp')
    with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(folder.rglob('*')):
            if p.is_file():z.write(p,p.relative_to(folder.parent).as_posix())
    with zipfile.ZipFile(temporary) as z:
        assert z.testzip() is None
        for row in records:assert hashlib.sha256(z.read(folder.name+'/'+row['path'])).hexdigest()==row['sha256']
    temporary.replace(archive);sha=hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_name(archive.name+'.sha256').write_text(sha+'  '+archive.name+'\n',encoding='ascii')
    return archive

def runtime_notices(folder):
    target=folder/'licenses/runtime';target.mkdir(parents=True,exist_ok=True)
    shutil.copy2(Path(sys.base_prefix)/'LICENSE.txt',target/'PYTHON-LICENSE.txt')
    versions={}
    for name in ('scapy','PySide6','PySide6_Essentials','PySide6_Addons','shiboken6','PyInstaller'):
        d=metadata.distribution(name);versions[name]=d.version
        dest=target/(name+'-'+d.version);dest.mkdir(exist_ok=True)
        for f in d.files or []:
            if ('license' in str(f).lower() or 'copying' in str(f).lower()) and Path(d.locate_file(f)).is_file():
                shutil.copy2(d.locate_file(f),dest/Path(f).name)
        (dest/'PACKAGE-LICENSE.txt').write_text(str(d.metadata.get('License-Expression') or d.metadata.get('License') or 'See the accompanying license files.')+'\n',encoding='utf-8')
    local=Path(__file__).resolve().parents[1]/'licenses'
    shutil.copy2(local/'LGPL-3.0.txt',target/'LGPL-3.0.txt')
    shutil.copy2(local/'REFERENCE-LICENSE.txt',target/'GPL-3.0.txt')
    import scapy
    src=Path(scapy.__file__).parent;dest=folder/'third-party-sources/scapy'
    shutil.copytree(src,dest,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.pyo'))
    (folder/'RUNTIME-COMPONENTS.md').write_text('''# Bundled runtime components

The portable package includes unmodified CPython, Scapy, PySide6/Qt, Shiboken
and a PyInstaller bootloader. Notices and open-source license texts are under
licenses/runtime. Scapy Python sources are under third-party-sources/scapy.
The matching meter source ZIP is published alongside the executable release.
Qt libraries remain separate DLLs; the Python source edition can be used to
rebuild the program. This package does not contain the Npcap installer, driver,
wpcap.dll or Packet.dll; install Npcap separately from its official site.

Corresponding upstream source locations:
- CPython: https://github.com/python/cpython/tree/v3.15.0rc3
- Scapy: https://github.com/secdev/scapy/tree/v2.8.0
- PySide/Shiboken: https://code.qt.io/cgit/pyside/pyside-setup.git/tag/?h=v6.12.0
- Qt: https://download.qt.io/archive/qt/6.12/6.12.0/single/
- PyInstaller (bootloader exception retained): https://github.com/pyinstaller/pyinstaller/tree/v6.22.3

Versions in this build:
'''+json.dumps({'Python':sys.version,**versions},indent=2)+'\n',encoding='utf-8')

def package(source,built,destination,status='not-run',resume=False):
    source=Path(source).resolve();built=Path(built).resolve();destination=Path(destination).resolve()
    if destination.exists():
        if not resume:raise ValueError('Choose a fresh output folder.')
        if (destination/'Aion2Meter.exe').read_bytes()!=(built/'Aion2Meter.exe').read_bytes():raise ValueError('Resume target is not this build.')
    if destination.is_relative_to(source) or destination.is_relative_to(built):raise ValueError('Output must be outside source/build directories.')
    files=list(built.rglob('*'))
    assert (built/'Aion2Meter.exe').is_file()
    assert not any(p.name.casefold() in {'wpcap.dll','packet.dll','npf.sys','npcap.sys'} for p in files)
    shutil.copytree(built,destination,dirs_exist_ok=resume)
    for name in ('LICENSE','CHANGELOG.md','CHANGELOG.de.md','THIRD-PARTY-NOTICES.md','LICENSE-STATUS.md'):shutil.copy2(source/name,destination/name)
    shutil.copytree(source/'licenses',destination/'licenses',dirs_exist_ok=resume);shutil.copytree(source/'docs',destination/'docs',dirs_exist_ok=resume)
    runtime_notices(destination)
    (destination/'README.md').write_text('''# Aion2Meter · Windows portable edition

Extract the complete ZIP and start Aion2Meter.exe. Keep _internal beside the
executable. Python and pip are not required. Npcap must be installed separately:
https://npcap.com/#download . The meter does not install drivers automatically.

Close the old meter before starting this version. Existing settings and logs
under LocalAppData/Aion2Meter are retained. Updates checks GitHub after a click;
downloads are verified and prepared separately, not silently installed.

See CHANGELOG.md for World/Abyss own-DPS, provisional late-start Entity rows,
time zones and known limits. The matching source ZIP remains available for
Python developers. Runtime license texts are under licenses/runtime.

Unsigned builds may be blocked by Windows application-control policies. No
security settings are changed by this package. A trusted signing certificate
or an administrator-approved execution environment is required where enforced.
See BUILD-STATUS.json for the validation status of this artifact.
''',encoding='utf-8')
    (destination/'README.de.md').write_text('''# Aion2Meter · Windows-Version zum Entpacken

Die komplette ZIP entpacken und Aion2Meter.exe starten. Der Ordner _internal
muss neben der EXE bleiben. Python und pip werden nicht benötigt. Npcap bleibt
eine separate Installation: https://npcap.com/#download . Das Meter installiert
keine Treiber automatisch.

Vorheriges Meter schließen. Einstellungen und Logs unter LocalAppData/Aion2Meter
bleiben erhalten. Updates fragt GitHub erst nach einem Klick ab; Downloads
werden geprüft und separat vorbereitet, nicht unbemerkt installiert.

CHANGELOG.de.md enthält World-/Abyss-Eigen-DPS, vorläufige Late-Start-Entity-
Zeilen, Zeitzonen und bekannte Grenzen. Das passende Quellcode-ZIP bleibt für
Python-Entwickler verfügbar. Lizenztexte liegen unter licenses/runtime.

Windows-Anwendungssteuerung kann unsignierte Builds blockieren. Dieses Paket
ändert keine Sicherheitseinstellungen. Wo eine solche Richtlinie aktiv ist,
braucht es eine vertrauenswürdige Signatur oder eine administrativ freigegebene
Ausführungsumgebung. BUILD-STATUS.json nennt den Prüfstatus dieses Pakets.
''',encoding='utf-8')
    (destination/'BUILD-STATUS.json').write_text(json.dumps({'version':version_of(source),'platform':'windows-x64','runtime_test':status,'signed':False,'driver_bundled':False},indent=2)+'\n',encoding='utf-8')
    return checksum_zip(destination)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--work',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--build-tools',type=Path)
    args=p.parse_args();source=args.source.resolve();work=args.work.resolve();output=args.output.resolve()
    if work.exists() or output.exists():raise ValueError('Use fresh work and output folders.')
    if work.is_relative_to(source) or output.is_relative_to(source):raise ValueError('Keep work/output outside the source tree.')
    work.mkdir(parents=True);version=version_of(source)
    if args.build_tools:sys.path.insert(0,str(args.build_tools.resolve()))
    import PyInstaller
    os.environ['PYTHONPATH']=os.pathsep.join(([str(args.build_tools.resolve())] if args.build_tools else [])+[str(source)])
    # DLL discovery must not pick unrelated developer tools from PATH.
    os.environ['PATH']=os.pathsep.join([str(Path(os.environ['WINDIR'])/'System32'),os.environ['WINDIR'],sys.base_prefix,str(Path(sys.executable).parent)])
    resource=work/'version.txt';resource.write_text(version_resource(version),encoding='utf-8')
    spec=work/'Aion2Meter.spec'
    spec.write_text(f'''from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules,collect_data_files
a=Analysis([{str(source/'tools/frozen_entry.py')!r}],pathex=[{str(source)!r}],binaries=[],datas=[({str(source/'meter/data')!r},'meter/data')]+collect_data_files('scapy'),hiddenimports=collect_submodules('scapy',on_error='ignore'),excludes=['meter.catalog_evidence','meter.catalog_checks','meter.catalog_validation','meter.skill_audit','PySide6.QtWebEngineWidgets','PySide6.QtWebEngineCore','tkinter','matplotlib','IPython'],noarchive=False)
a.binaries=[x for x in a.binaries if Path(x[0]).name.casefold() not in ('wpcap.dll','packet.dll','npf.sys','npcap.sys')]
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,[],exclude_binaries=True,name='Aion2Meter',console=False,upx=False,version={str(resource)!r})
coll=COLLECT(exe,a.binaries,a.datas,name='Aion2Meter',upx=False)
''',encoding='utf-8')
    subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--distpath',str(work/'dist'),'--workpath',str(work/'build'),str(spec)],env=os.environ,check=True)
    print(package(source,work/'dist/Aion2Meter',output))

if __name__=='__main__':main()
