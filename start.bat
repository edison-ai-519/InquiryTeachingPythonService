@echo off
setlocal
cd /d "%~dp0"

where powershell.exe >nul 2>nul
if errorlevel 1 (
  echo PowerShell was not found.
  exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-dev.ps1" %*
set "START_EXIT_CODE=%errorlevel%"
if not "%START_EXIT_CODE%"=="0" (
  echo.
  echo Startup failed. Review the error above, then press any key to close this window.
  pause >nul
)
exit /b %START_EXIT_CODE%
