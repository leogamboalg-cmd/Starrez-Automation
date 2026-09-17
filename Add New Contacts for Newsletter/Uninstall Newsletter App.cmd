@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\uninstall_app.ps1"
if errorlevel 1 (
  echo.
  echo Uninstall failed. Review the error above.
  pause
  exit /b 1
)
echo.
echo Uninstall complete. You can close this window.
pause
