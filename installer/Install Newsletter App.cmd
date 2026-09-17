@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install_app.ps1"
if errorlevel 1 (
  echo.
  echo Installation failed. Review the error above.
  pause
  exit /b 1
)
echo.
echo Installation complete. You can close this window.
pause
