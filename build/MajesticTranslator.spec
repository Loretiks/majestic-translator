# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Majestic Translator.

Run from the repo root:

    pyinstaller build/MajesticTranslator.spec --noconfirm

Outputs `dist/MajesticTranslator/MajesticTranslator.exe` plus the runtime
folder (Qt plugins, paddle DLLs, ML models). The folder is what the Inno
Setup installer wraps for distribution.
"""
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_data_files

ROOT = Path(SPECPATH).resolve().parent
APP_NAME = "MajesticTranslator"

# PaddleOCR / PaddleX / paddle ship a lot of YAML configs, vocab files,
# and weights that PyInstaller's static analysis misses. collect_all
# pulls every Python module + every data file in the package.
hidden = []
datas = []
binaries = []

for pkg in ("paddleocr", "paddlex", "paddle"):
    p_datas, p_binaries, p_hidden = collect_all(pkg)
    datas += p_datas
    binaries += p_binaries
    hidden += p_hidden

# Other transitive deps that need data files.
for pkg in ("shapely", "rapidfuzz", "lazy_loader"):
    try:
        datas += collect_data_files(pkg)
    except Exception:
        pass

# Bring our own source tree in as data so relative imports inside the
# frozen exe still find app/i18n.py, app/themes.py, etc.
datas += [(str(ROOT / "app"), "app")]


a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden + [
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Big optional pieces of the paddle/paddlex universe that the
        # chat translator never touches. Excluded to keep size sane.
        "matplotlib",
        "scipy",
        "torch",
        "tensorflow",
        "jupyter",
        "notebook",
        "IPython",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
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
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=APP_NAME,
)
