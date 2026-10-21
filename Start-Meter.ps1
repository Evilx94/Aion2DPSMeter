$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$meterPython = Join-Path $PSScriptRoot '.venv/Scripts/pythonw.exe'
$meterArgs = @('-m', 'meter')
$localConfig = Join-Path $PSScriptRoot 'local-runtime.json'
if (Test-Path -LiteralPath $localConfig) {
    $runtimeSettings = Get-Content -LiteralPath $localConfig -Raw | ConvertFrom-Json
    if ($runtimeSettings.python) { $meterPython = [string]$runtimeSettings.python }
}
if (-not (Test-Path -LiteralPath $meterPython)) {
    $meterLauncher = Get-Command pyw -ErrorAction SilentlyContinue
    if (-not $meterLauncher) { $meterLauncher = Get-Command py -ErrorAction SilentlyContinue }
    if (-not $meterLauncher) { throw 'Python 3.15 wird benötigt. Siehe README.md.' }
    $meterPython = $meterLauncher.Source
    $meterArgs = @('-3.15') + $meterArgs
}
Start-Process -FilePath $meterPython -ArgumentList $meterArgs -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
