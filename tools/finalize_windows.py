"""Verify a SignPath EXE, then regenerate the release manifest, ZIP and SHA-256."""
from pathlib import Path
import argparse
import json
import os
import shutil
import subprocess
import sys

from build_windows import checksum_zip


def verify_signature(executable, expected_version):
    # Fixed command text; all external strings are passed as environment data.
    # No execution-policy changes or command interpolation are needed.
    script = r'''
        $ErrorActionPreference = 'Stop'
        $File = $env:AION2_SIGNATURE_FILE
        $ExpectedVersion = $env:AION2_SIGNATURE_VERSION
        $v = [System.Diagnostics.FileVersionInfo]::GetVersionInfo($File)
        if ($v.ProductName -ne 'Aion2Meter' -or $v.OriginalFilename -ne 'Aion2Meter.exe' -or $v.ProductVersion -ne $ExpectedVersion) { throw 'Returned EXE metadata differs from the expected release' }
        $s = Get-AuthenticodeSignature -LiteralPath $File
        if ($s.Status -ne 'Valid' -or $null -eq $s.SignerCertificate) { throw "Signature is not valid: $($s.Status)" }
        if ($null -eq $s.TimeStamperCertificate) { throw 'Timestamp is missing' }
        [pscustomobject]@{subject=$s.SignerCertificate.Subject; thumbprint=$s.SignerCertificate.Thumbprint; timestamped=$true} | ConvertTo-Json -Compress
    '''
    env={**os.environ,'AION2_SIGNATURE_FILE':str(executable.resolve()),'AION2_SIGNATURE_VERSION':expected_version}
    env['PSModulePath']=str(Path(os.environ['WINDIR'])/'System32/WindowsPowerShell/v1.0/Modules')
    result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],env=env,capture_output=True,text=True,check=True)
    return json.loads(result.stdout)


def finalize(folder, signed_executable):
    folder=Path(folder).resolve(); signed_executable=Path(signed_executable).resolve()
    status_file=folder/'BUILD-STATUS.json'
    status=json.loads(status_file.read_text(encoding='utf-8'))
    if status.get('platform')!='windows-x64' or status.get('signed') is not False:
        raise ValueError('Expected an unsigned Windows build')
    if not signed_executable.is_file() or signed_executable.name!='Aion2Meter.exe':
        raise ValueError('Expected the returned Aion2Meter.exe')
    signature=verify_signature(signed_executable,status['version'])
    shutil.copy2(signed_executable,folder/'Aion2Meter.exe')
    status.update(signed=True, signature=signature)
    status_file.write_text(json.dumps(status,indent=2)+'\n',encoding='utf-8')
    return checksum_zip(folder)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--folder',type=Path,required=True)
    p.add_argument('--signed-exe',type=Path,required=True)
    a=p.parse_args()
    print(finalize(a.folder,a.signed_exe))

