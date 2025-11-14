# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

import os
project_dir = os.path.dirname(os.path.abspath(SPEC))

datas = [
    (os.path.join(project_dir, 'bot'), 'bot'),
    (os.path.join(project_dir, 'AVIS'), 'AVIS'),
    (os.path.join(project_dir, 'config.yaml'), '.'),
    (os.path.join(project_dir, '.env'), '.'),
]
binaries = []
hiddenimports = [
    'selenium', 'undetected_chromedriver', 'selenium_stealth', 
    'tkinter', 'yaml', 'dotenv', 'psutil', 'dateutil',
    'win10toast',  # Pour notifications (#21)
    'matplotlib', 'matplotlib.pyplot', 'matplotlib.backends.backend_tkagg',  # Pour graphiques (#22)
]
tmp_ret = collect_all('selenium')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('undetected_chromedriver')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('selenium_stealth')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['gui.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    name='MedalBot',
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
    icon='NONE',
)
