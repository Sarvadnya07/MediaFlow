# -*- mode: python ; coding: utf-8 -*-
import sys
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

# Collect yt_dlp extractors and dependencies
hiddenimports = [
    'app',
    'app.engine',
    'app.engine.protocol',
    'app.engine.sidecar',
    'app.engine.queue_manager',
    'app.engine.queue_models',
    'app.services.yt_service',
    'app.services.ffmpeg_service',
    'app.security',
    'app.logging_config',
    'sqlite3',
    'sqlalchemy',
    'sqlalchemy.dialects.sqlite',
] + collect_submodules('yt_dlp')

datas = collect_data_files('yt_dlp')

a = Analysis(
    ['sidecar_entrypoint.py'],
    pathex=['..', '.'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'celery', 'redis'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='mediadock-sidecar',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
