@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Setup-Meter.ps1"
set "meterSetupExit=%errorlevel%"
echo.
pause
exit /b %meterSetupExit%
