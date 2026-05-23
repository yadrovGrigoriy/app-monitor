# -*- mode: python ; coding: utf-8 -*-
"""
Spec-файл для сборки AppMonitor через PyInstaller.
Запуск: pyinstaller appmonitor.spec
"""

import os
import sys
from pathlib import Path

# В .spec файле нет __file__, используем os.getcwd()
PROJECT_ROOT = Path(os.getcwd()).resolve()
APP_NAME = 'AppMonitor'

a = Analysis(
    [str(PROJECT_ROOT / 'main.py')],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=[
        (str(PROJECT_ROOT / 'data'), 'data'),
    ],
    hiddenimports=[
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'PyQt5.QtSvg',
        'win32api',
        'win32event',
        'win32security',
        'win32gui',
        'win32con',
        'winerror',
        'ntsecuritycon',
        'psutil',
        'schedule',
        'fastapi',
        'uvicorn',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'httpx',
        'pydantic',
        'asyncio',
        'ctypes',
        'smtplib',
        'email.mime.text',
        'email.mime.multipart',
        'email.mime.base',
        'email.encoders',
        'multiprocessing',
        'multiprocessing.queues',
    ],
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
    name=APP_NAME,
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
    icon=str(PROJECT_ROOT / 'app_icon.ico') if (PROJECT_ROOT / 'app_icon.ico').exists() else None,
)
