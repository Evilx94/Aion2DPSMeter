# Set up this source package; never install Python or a driver automatically.
[CmdletBinding()]
param([switch]$CheckOnly, [string]$PythonPath)
$ErrorActionPreference = 'Stop'
$previousAutoInstall = [Environment]::GetEnvironmentVariable('PYTHON_MANAGER_AUTOMATIC_INSTALL', 'Process')
$previousBytecode = [Environment]::GetEnvironmentVariable('PYTHONDONTWRITEBYTECODE', 'Process')
$env:PYTHON_MANAGER_AUTOMATIC_INSTALL = 'false'
$env:PYTHONDONTWRITEBYTECODE = '1'
$setupExit = 1
try {
    Write-Host 'Aion2Meter - Setup' -ForegroundColor Cyan
    Write-Host 'This sets up Python packages locally. Python and Npcap are installed separately.'
    $requirements = Join-Path $PSScriptRoot 'requirements.txt'
    if (-not (Test-Path -LiteralPath $requirements)) { throw 'requirements.txt is missing. Extract the complete meter ZIP first.' }
    $environmentPath = Join-Path $PSScriptRoot '.venv'
    $environmentPython = Join-Path $environmentPath 'Scripts/python.exe'
    $runtime = $null
    $runtimeArgs = @()
    if ($PythonPath) {
        if (-not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) { throw 'The supplied PythonPath does not exist.' }
        $runtime = $PythonPath
    } elseif (Test-Path -LiteralPath $environmentPython -PathType Leaf) {
        $runtime = $environmentPython
    } else {
        $launcher = Get-Command py -CommandType Application -ErrorAction SilentlyContinue
        if ($launcher) { $runtime = $launcher.Source; $runtimeArgs = @('-3.15') }
    }
    if (-not $runtime) {
        throw 'Python 3.15 (64-bit) is required. Install it from https://www.python.org/downloads/windows/ including its launcher, then run Setup-Meter.cmd again.'
    }
    & $runtime @runtimeArgs -c 'import sys,struct; print(sys.version); sys.exit(0 if sys.version_info[:2] == (3,15) and sys.maxsize > 2**32 else 1)'
    if ($LASTEXITCODE -ne 0) { throw 'A working 64-bit Python 3.15 runtime is required. See https://www.python.org/downloads/windows/ . No runtime was installed by this setup.' }
    $npcapDll = Join-Path $env:WINDIR 'System32/Npcap/wpcap.dll'
    $npcapService = Get-Service -Name npcap -ErrorAction SilentlyContinue
    $npcapPresent = (Test-Path -LiteralPath $npcapDll) -and ($null -ne $npcapService)
    if ($npcapPresent) {
        Write-Host ('Npcap detected (driver: ' + $npcapService.Status + '). Actual capture access is checked when the meter starts.') -ForegroundColor Green
    } else {
        Write-Host 'Npcap was not detected. Install it separately from https://npcap.com/#download and accept any requested restart.' -ForegroundColor Yellow
        Write-Host 'The driver installer needs administrator approval. Setup does not download or install drivers.'
    }
    if ($CheckOnly) {
        Write-Host 'Check only: no environment or packages will be created or installed.'
        & $runtime @runtimeArgs -c 'import scapy,PySide6; print(scapy.__name__,scapy.__version__,PySide6.__name__,PySide6.__version__)'
        if ($LASTEXITCODE -ne 0) { throw 'Required Python packages are missing from the checked runtime. Run Setup-Meter.cmd to set up the local environment.' }
    } else {
        if (-not (Test-Path -LiteralPath $environmentPython -PathType Leaf)) {
            if (Test-Path -LiteralPath $environmentPath) { throw 'An incomplete .venv folder exists. Rename it before retrying; setup will not remove your files.' }
            Write-Host 'Creating the local .venv environment...'
            & $runtime @runtimeArgs -m venv $environmentPath
            if ($LASTEXITCODE -ne 0) { throw 'Could not create .venv. Check folder permissions and the Python installation.' }
        }
        & $environmentPython -c 'import sys,struct; sys.exit(0 if sys.version_info[:2] == (3,15) and sys.maxsize > 2**32 else 1)'
        if ($LASTEXITCODE -ne 0) { throw 'The existing .venv needs 64-bit Python 3.15. Rename that folder before retrying.' }
        Write-Host 'Installing the packages from requirements.txt (Internet access required)...'
        & $environmentPython -m pip install -r $requirements
        if ($LASTEXITCODE -ne 0) { throw 'Package installation failed. Check the error above and retry Setup-Meter.cmd. The meter has not been started.' }
        & $environmentPython -c 'import scapy,PySide6; print(scapy.__name__,scapy.__version__,PySide6.__name__,PySide6.__version__)'
        if ($LASTEXITCODE -ne 0) { throw 'The installed packages could not be imported. See the error above.' }
        Write-Host 'Python packages are ready. Start the meter using Start-Meter.cmd.' -ForegroundColor Green
    }
    if ($npcapPresent) { $setupExit = 0 } else { $setupExit = 2; Write-Host 'Npcap is still required for live capture. See README.md.' -ForegroundColor Yellow }
} catch {
    Write-Host ('Setup could not finish: ' + $_.Exception.Message) -ForegroundColor Red
    Write-Host 'See README.md > Installation (Windows) for the manual steps.'
    $setupExit = 1
} finally {
    [Environment]::SetEnvironmentVariable('PYTHON_MANAGER_AUTOMATIC_INSTALL', $previousAutoInstall, 'Process')
    [Environment]::SetEnvironmentVariable('PYTHONDONTWRITEBYTECODE', $previousBytecode, 'Process')
}
exit $setupExit
