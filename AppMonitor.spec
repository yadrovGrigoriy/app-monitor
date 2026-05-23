# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['run_app.py'],
    pathex=[],
    binaries=[],
    datas=[('data', 'data')],
    icon='data/appmonitor.ico',
    hiddenimports=['PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets', 'PyQt5.QtSvg', 'win32api', 'win32event', 'win32file', 'win32pipe', 'win32process', 'win32security', 'win32service', 'win32serviceutil', 'win32timezone', 'winerror', 'pywintypes', 'psutil', 'schedule', 'fastapi', 'uvicorn', 'uvicorn.logging', 'uvicorn.loops', 'uvicorn.loops.auto', 'uvicorn.protocols', 'uvicorn.protocols.http.auto', 'uvicorn.protocols.websockets.auto', 'websockets', 'httpx', 'pydantic', 'cryptography', 'zeroconf', 'matplotlib', 'matplotlib.backends.backend_qt5agg', 'matplotlib.backends.backend_agg', 'matplotlib.backend_bases', 'PIL', 'PIL._imaging', 'PIL._imagingtk', 'PIL.Image', 'PIL.ImageDraw', 'PIL.ImageFont'],
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
    name='AppMonitor',
    icon='data/appmonitor.ico',
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
