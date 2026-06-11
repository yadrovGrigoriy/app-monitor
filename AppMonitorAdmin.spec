# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec для AppMonitorAdmin.exe — удалённая админ-панель."""

import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ['run_admin.py'],
    pathex=[r'C:\code\AppMonitor'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'PyQt5.sip',
        'core.database',
        'core.auth',
        'core.role_manager',
        'core.logger',
        'core.updater',
        'core.reporter',
        'core.notifier',
        'ui.admin_ui',
        'ui.base_ui',
        'ui.theme_manager',
        'ui.app_icon',
        'ui.styles',
        'ui.widgets.activity_table',
        'ui.widgets.bottom_bar',
        'ui.widgets.date_toolbar',
        'ui.widgets.tracked_table',
        'ui.dialogs.auth_dialogs',
        'ui.dialogs.limit_dialog',
        'ui.dialogs.settings_dialog',
        'ui.dialogs.stats_dialog',
        'api.admin_server',
        'api.server',
        'api.schemas',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'cv2',
        'pandas',
        'scipy',
        'IPython',
        'jupyter',
        'notebook',
        'setuptools',
        'pip',
        'wheel',
        'pkg_resources',
        'test',
        'pytest',
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
    name='AppMonitorAdmin',
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
    icon='data/appmonitor_admin.ico',
)
