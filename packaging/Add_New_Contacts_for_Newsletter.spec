from pathlib import Path


project_dir = Path(SPECPATH).parent
asset_names = (
    "app_logo.ico",
    "cancel_button.png",
    "contact_status.png",
    "excel.png",
    "green_plus.png",
    "last_name_area.png",
    "last_name_label.png",
    "link.png",
    "main.png",
    "whiteLink.png",
)

added_data = [
    (str(project_dir / "assets" / asset_name), "assets")
    for asset_name in asset_names
]

a = Analysis(
    [str(project_dir / "src" / "app_entry.py")],
    pathex=[str(project_dir / "src")],
    binaries=[],
    datas=added_data,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Add New Contacts for Newsletter",
    icon=str(project_dir / "assets" / "app_logo.ico"),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
