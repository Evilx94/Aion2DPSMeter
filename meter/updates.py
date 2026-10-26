"""Explicit GitHub update checks and verified, non-executing package staging.

No settings, capture, install-directory or interpreter changes. HTTPS origin,
version, SHA-256, ZIP paths and the source manifest are checked before staging.
"""
from pathlib import Path,PurePosixPath
from urllib.request import Request,urlopen
from urllib.parse import urlsplit,quote,unquote
from urllib.error import HTTPError,URLError
from threading import Event
from dataclasses import dataclass
from tempfile import TemporaryDirectory
import hashlib,json,re,sys,zipfile,stat,uuid,ast

REPOSITORY='Evilx94/Aion2DPSMeter'
RELEASES_URL='https://github.com/'+REPOSITORY+'/releases'
API_URL='https://api.github.com/repos/'+REPOSITORY+'/releases?per_page=30'
MAX_DOWNLOAD=512*1024*1024
MAX_UNPACKED=2*1024*1024*1024
MAX_FILES=12000
VERSION=re.compile(r'^v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-(alpha|beta|rc)(?:\.?([1-9]\d*|0))?)?$')
ERRORS={
 'network':'GitHub could not be reached. Please try again later.',
 'cancelled':'Update cancelled.',
 'metadata':'Invalid release information.',
 'url':'Update URL is outside the official repository.',
 'checksum_missing':'This release has no SHA-256 checksum. Open its GitHub page instead.',
 'checksum':'The downloaded package failed SHA-256 verification.',
 'package':'The update package or its source manifest is invalid.',
 'size':'The update exceeds the allowed size.',
 'asset':'No compatible update package is attached to this release.',
 'version':'The update is not newer than the installed version.',
 'storage':'The update could not be saved. Check free space and folder access.',
}

class UpdateError(Exception):
    def __init__(self,code):self.code=code;super().__init__(ERRORS.get(code,code))

def version_key(value):
    if not isinstance(value,str) or len(value)>80:raise UpdateError('metadata')
    m=VERSION.fullmatch(value)
    if not m:raise UpdateError('metadata')
    major,minor,patch,kind,n=m.groups()
    return (int(major),int(minor),int(patch),{'alpha':0,'beta':1,'rc':2,None:3}[kind],int(n or 0))

def cancelled(event):
    if event is not None and event.is_set():raise UpdateError('cancelled')

def asset_url(url,tag,name):
    if not isinstance(url,str):raise UpdateError('url')
    parts=urlsplit(url)
    expected='/'+REPOSITORY+'/releases/download/'+tag+'/'+name
    if (parts.scheme!='https' or parts.netloc!='github.com' or parts.query or parts.fragment
            or unquote(parts.path)!=expected):raise UpdateError('url')
    return url

def digest_value(asset):
    value=asset.get('digest','')
    return value[7:].lower() if isinstance(value,str) and re.fullmatch(r'sha256:[0-9a-fA-F]{64}',value) else ''

@dataclass(frozen=True)
class Release:
    tag:str
    version:str
    notes:str
    prerelease:bool
    package_name:str=''
    package_url:str=''
    size:int=0
    digest:str=''
    checksum_url:str=''
    mode:str='source'
    @property
    def page_url(self):return RELEASES_URL+'/tag/'+quote(self.tag,safe='')
    @property
    def verifiable(self):return bool(self.package_url and (self.digest or self.checksum_url))

def parse_releases(data,include_prereleases=True,mode='source'):
    if not isinstance(data,list) or len(data)>100 or mode not in ('source','windows-x64'):raise UpdateError('metadata')
    candidates=[]
    for item in data:
        if not isinstance(item,dict) or item.get('draft'):continue
        tag=item.get('tag_name','')
        try:key=version_key(tag)
        except UpdateError:continue
        pre=bool(item.get('prerelease')) or key[3]<3
        if pre and not include_prereleases:continue
        version=tag.removeprefix('v')
        notes=item.get('body') or ''
        if not isinstance(notes,str):continue
        # Keep metadata display plain-text and bounded, never rendered as HTML.
        notes=notes[:100000]
        assets=item.get('assets',[])
        if not isinstance(assets,list):continue
        suffix='' if mode=='source' else '-windows-x64'
        name='Aion2Meter-'+version+suffix+'.zip'
        matching=[a for a in assets if isinstance(a,dict) and a.get('name')==name]
        sums=[a for a in assets if isinstance(a,dict) and a.get('name')==name+'.sha256']
        args={}
        if len(matching)==1:
            a=matching[0];size=a.get('size',0)
            if type(size) is int and 0<size<=MAX_DOWNLOAD:
                try:
                    url=asset_url(a.get('browser_download_url'),tag,name)
                    checksum=asset_url(sums[0].get('browser_download_url'),tag,name+'.sha256') if len(sums)==1 else ''
                    args=dict(package_name=name,package_url=url,size=size,digest=digest_value(a),checksum_url=checksum)
                except UpdateError:pass
        candidates.append(Release(tag,version,notes,pre,mode=mode,**args))
    return sorted(candidates,key=lambda r:version_key(r.version),reverse=True)

def _open(url):
    from . import __version__
    try:
        response=urlopen(Request(url,headers={'User-Agent':'Aion2Meter/'+__version__,'Accept':'application/vnd.github+json' if url==API_URL else 'application/octet-stream'}),timeout=12)
        target=urlsplit(response.geturl())
        allowed={'api.github.com'} if url==API_URL else {'github.com','release-assets.githubusercontent.com','objects.githubusercontent.com'}
        if target.scheme!='https' or target.hostname not in allowed:
            response.close();raise UpdateError('url')
        return response
    except (HTTPError,URLError,TimeoutError,OSError) as exc:raise UpdateError('network') from exc

def read_small(url,limit,cancel=None):
    cancelled(cancel)
    with _open(url) as r:
        data=r.read(limit+1)
    cancelled(cancel)
    if len(data)>limit:raise UpdateError('size')
    return data

def check_updates(current,include_prereleases=True,mode=None,cancel=None):
    version_key(current)
    raw=read_small(API_URL,2*1024*1024,cancel)
    try:data=json.loads(raw)
    except (ValueError,UnicodeError) as exc:raise UpdateError('metadata') from exc
    releases=parse_releases(data,include_prereleases,mode or ('windows-x64' if getattr(sys,'frozen',False) else 'source'))
    latest=releases[0] if releases else None
    return {'current':current,'latest':latest,'available':bool(latest and version_key(latest.version)>version_key(current))}

def expected_checksum(release,cancel=None):
    if release.digest:return release.digest
    if not release.checksum_url:raise UpdateError('checksum_missing')
    asset_url(release.checksum_url,release.tag,release.package_name+'.sha256')
    raw=read_small(release.checksum_url,4096,cancel)
    try:text=raw.decode('ascii').strip()
    except UnicodeError as exc:raise UpdateError('checksum') from exc
    m=re.fullmatch(r'([0-9a-fA-F]{64})\s+\*?'+re.escape(release.package_name),text)
    if not m:raise UpdateError('checksum')
    return m[1].lower()

def safe_relative(name):
    if (not isinstance(name,str) or not name or len(name)>240 or '\\' in name or ':' in name
            or any(ord(c)<32 for c in name)):raise UpdateError('package')
    p=PurePosixPath(name)
    parts=name.rstrip('/').split('/')
    reserved={'con','prn','aux','nul'}|{f'{prefix}{i}' for prefix in ('com','lpt') for i in range(1,10)}
    if p.is_absolute() or any(not v or v in ('.','..') or v.rstrip(' .')!=v or v.split('.')[0].casefold() in reserved for v in parts):raise UpdateError('package')
    return p

def validate_package(path,release):
    root='Aion2Meter-'+release.version
    if release.mode=='windows-x64':root+='-windows-x64'
    try:
        with zipfile.ZipFile(path) as z:
            entries=z.infolist()
            if len(entries)>MAX_FILES or sum(e.file_size for e in entries)>MAX_UNPACKED:raise UpdateError('size')
            seen=set();files={}
            for item in entries:
                rel=safe_relative(item.filename);parts=rel.parts
                if len(parts)<1 or parts[0]!=root:raise UpdateError('package')
                key=str(rel).casefold()
                if key in seen:raise UpdateError('package')
                seen.add(key)
                if stat.S_ISLNK(item.external_attr>>16) or item.flag_bits&1:raise UpdateError('package')
                if not item.is_dir():
                    if len(parts)<2:raise UpdateError('package')
                    files['/'.join(parts[1:])]=item
            manifest_entry=files.get('SOURCE-MANIFEST.json')
            if not manifest_entry or manifest_entry.file_size>2*1024*1024:raise UpdateError('package')
            manifest=json.loads(z.read(manifest_entry))
            if not isinstance(manifest,list) or len(manifest)>MAX_FILES:raise UpdateError('package')
            declared={}
            for row in manifest:
                if not isinstance(row,dict):raise UpdateError('package')
                name=row.get('path');safe_relative(name);sha=row.get('sha256','')
                if name in declared or not isinstance(sha,str) or not re.fullmatch('[0-9a-f]{64}',sha):raise UpdateError('package')
                declared[name]=sha
            if set(files)-{'SOURCE-MANIFEST.json'}!=set(declared):raise UpdateError('package')
            required={'meter/__init__.py','Start-Meter.cmd','requirements.txt'} if release.mode=='source' else {'Aion2Meter.exe'}
            if not required<=files.keys():raise UpdateError('package')
            if release.mode=='source':
                if files['meter/__init__.py'].file_size>65536:raise UpdateError('package')
                tree=ast.parse(z.read(files['meter/__init__.py']).decode('utf-8'))
                versions=[n.value.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='__version__' for t in n.targets) and isinstance(n.value,ast.Constant)]
                if versions!=[release.version]:raise UpdateError('package')
            for name,sha in declared.items():
                h=hashlib.sha256()
                with z.open(files[name]) as stream:
                    for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
                if h.hexdigest()!=sha:raise UpdateError('package')
            return root
    except (zipfile.BadZipFile,ValueError,UnicodeError,KeyError,RuntimeError,SyntaxError,NotImplementedError) as exc:raise UpdateError('package') from exc

def prepare_update(release,current,directory,cancel=None,progress=None):
    if version_key(release.version)<=version_key(current):raise UpdateError('version')
    expected_name='Aion2Meter-'+release.version+('-windows-x64' if release.mode=='windows-x64' else '')+'.zip'
    if (release.mode not in ('source','windows-x64') or release.package_name!=expected_name
            or type(release.size) is not int or not 0<release.size<=MAX_DOWNLOAD):raise UpdateError('asset')
    if not release.package_url:raise UpdateError('asset')
    asset_url(release.package_url,release.tag,release.package_name)
    expected=expected_checksum(release,cancel)
    base=Path(directory).resolve()/'updates';base.mkdir(parents=True,exist_ok=True)
    # All temporary writes stay outside the live program and user log folders.
    try:
        with TemporaryDirectory(prefix='.download-',dir=base) as tmp:
            temporary=Path(tmp);archive=temporary/release.package_name
            total=0;h=hashlib.sha256();cancelled(cancel)
            with _open(release.package_url) as response,archive.open('wb') as target:
                while True:
                    cancelled(cancel);block=response.read(128*1024)
                    if not block:break
                    total+=len(block)
                    if total>MAX_DOWNLOAD or total>release.size:raise UpdateError('size')
                    target.write(block);h.update(block)
                    if progress:progress(total,release.size)
            if total!=release.size or h.hexdigest()!=expected:raise UpdateError('checksum')
            cancelled(cancel);root=validate_package(archive,release)
            stage=temporary/'prepared';stage.mkdir()
            with zipfile.ZipFile(archive) as z:
                for info in z.infolist():
                    cancelled(cancel);relative=safe_relative(info.filename)
                    path=(stage/Path(*relative.parts)).resolve()
                    if not path.is_relative_to(stage.resolve()):raise UpdateError('package')
                    if info.is_dir():path.mkdir(parents=True,exist_ok=True);continue
                    path.parent.mkdir(parents=True,exist_ok=True)
                    with z.open(info) as source,path.open('xb') as dest:
                        for block in iter(lambda:source.read(1024*1024),b''):
                            cancelled(cancel);dest.write(block)
            cancelled(cancel)
            final=base/(release.version+'-'+uuid.uuid4().hex[:10]);stage.rename(final)
            return {'version':release.version,'directory':str(final/root),'sha256':expected,'mode':release.mode}
    except OSError as exc:raise UpdateError('storage') from exc
