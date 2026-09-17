# Starrez-Automation

## Run from source

```powershell
pip install -r requirements.txt
python src\guiLauncher.py
```

Run the automated tests with:

```powershell
python -m unittest discover -s tests -t .
```

## Build the Windows desktop app

Install the build dependency once:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
```

Build the single-file app:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\packaging\build_app.ps1
```

The distributable app is created at:

```text
dist\Add New Contacts for Newsletter.exe
```

The app is a self-contained 64-bit Windows executable. Recipients do not need
Python or this source repository. The selected Excel workbook preference is
stored separately for each Windows user in Local AppData.

The distribution ZIP also contains a per-user installer. It creates the
Desktop shortcut and an invisible scheduled task that checks the synced
newsletter response CSV once per hour. During installation, the user selects
the locally synced shared responses CSV once; its path is saved in that user's
Local AppData. The scheduled mode exits after each check and does not keep a
tray process running.

## Repository layout

- `assets/` contains the application icon and StarRez screen-recognition images.
- `docs/` contains the end-user installation guide.
- `installer/` contains the user-facing launchers and their PowerShell scripts.
- `packaging/` contains the executable and ZIP build configuration.
- `src/` contains the application source code.
- `tests/` contains the automated test suite.
