# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Drama Reels — Windows build."""

import os
import sys

block_cipher = None

# Collect data files
datas = [
    ('templates', 'templates'),
    ('config.py', '.'),
    ('config_win.py', '.'),
    ('app.py', '.'),
    ('processor.py', '.'),
    ('translator.py', '.'),
    ('thumbnail.py', '.'),
    ('content_gen.py', '.'),
    ('scheduler.py', '.'),
    ('uploader.py', '.'),
    ('database.py', '.'),
]

# Hidden imports
hiddenimports = [
    'flask',
    'flask.app',
    'flask.templating',
    'jinja2',
    'sqlite3',
    'json',
    'threading',
    'webbrowser',
    'ctypes',
    'urllib.request',
    'urllib.parse',
    'http.server',
    'faster_whisper',
    'imageio_ffmpeg',
]

a = Analysis(
    ['app_windows.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'matplotlib', 'numpy.testing', 'scipy',
        'pandas', 'PIL', 'cv2', 'torch', 'tensorflow',
    ],
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
    name='DramaReels',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Console for logs
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico' if os.path.exists('icon.ico') else None,
)
