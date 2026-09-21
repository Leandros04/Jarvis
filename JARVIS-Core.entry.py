# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

root = Path.cwd().resolve()
icon_file = root / "assets" / "jarvis.ico"
version_file = root / "packaging" / "version_info.txt"
runtime_hook = root / "hooks" / "runtime_playwright.py"

# Packages with runtime discovery, native binaries, or bundled data that are
# safer to collect explicitly. PyInstaller's built-in hooks still handle the
# rest of the dependency graph.
collect_packages = [
    "openai",
    "playwright",
    "faster_whisper",
    "ctranslate2",
    "tokenizers",
    "huggingface_hub",
    "openwakeword",
    "onnxruntime",
    "sounddevice",
    "pyttsx3",
    "pycaw",
    "comtypes",
    "pystray",
    "winotify",
]

extra_datas = []
extra_binaries = []
extra_hidden = [
    "jarvis",
    "pyttsx3.drivers",
    "pyttsx3.drivers.sapi5",
]

for package in collect_packages:
    try:
        d, b, h = collect_all(package)
        extra_datas += d
        extra_binaries += b
        extra_hidden += h
    except Exception as exc:
        print(f"[spec] collect_all({package!r}) skipped: {exc}")

core_a = Analysis(
    [str(root / "packaging" / "JARVIS-Core.entry.py")],
    pathex=[str(root)],
    binaries=extra_binaries,
    datas=extra_datas,
    hiddenimports=extra_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(runtime_hook)],
    excludes=[],
    noarchive=False,
    optimize=0,
)

tray_a = Analysis(
    [str(root / "packaging" / "JARVIS-Tray.entry.py")],
    pathex=[str(root)],
    binaries=[],
    datas=[],
    hiddenimports=[
        "pystray._win32",
        "PIL.Image",
        "PIL.ImageDraw",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

core_pyz = PYZ(core_a.pure)
tray_pyz = PYZ(tray_a.pure)

core_exe = EXE(
    core_pyz,
    core_a.scripts,
    [],
    exclude_binaries=True,
    name="JARVIS-Core",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon_file),
    version=str(version_file),
)

tray_exe = EXE(
    tray_pyz,
    tray_a.scripts,
    [],
    exclude_binaries=True,
    name="JARVIS",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon_file),
    version=str(version_file),
)

coll = COLLECT(
    core_exe,
    tray_exe,
    core_a.binaries,
    core_a.datas,
    tray_a.binaries,
    tray_a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="JARVIS",
)
