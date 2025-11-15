# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files

import os
import sys
import logging
logger = logging.getLogger()

# Importer yaml pour trouver son chemin et ses binaires
yaml_datas = []
yaml_binaries = []
try:
    import yaml
    yaml_path = os.path.dirname(yaml.__file__)
    # Ajouter le répertoire yaml aux données
    yaml_datas = [(yaml_path, 'yaml')]
    
    # Chercher les fichiers binaires (_yaml.pyd, _yaml.so, etc.)
    for file in os.listdir(yaml_path):
        if file.startswith('_yaml') and (file.endswith('.pyd') or file.endswith('.so') or file.endswith('.dll')):
            yaml_binaries.append((os.path.join(yaml_path, file), '.'))
except ImportError:
    pass

# Importer undetected_chromedriver pour trouver son chemin
uc_datas = []
uc_binaries = []
try:
    import undetected_chromedriver
    uc_path = os.path.dirname(undetected_chromedriver.__file__)
    # Ajouter le répertoire undetected_chromedriver aux données
    uc_datas = [(uc_path, 'undetected_chromedriver')]
    logger.info(f"undetected_chromedriver trouvé: {uc_path}")
except ImportError:
    # Si le module n'est pas installé, chercher dans site-packages
    import site
    for site_packages in site.getsitepackages():
        uc_candidate = os.path.join(site_packages, 'undetected_chromedriver')
        if os.path.exists(uc_candidate):
            uc_datas = [(uc_candidate, 'undetected_chromedriver')]
            logger.info(f"undetected_chromedriver trouvé dans site-packages: {uc_candidate}")
            break
    # Si toujours pas trouvé, chercher dans le répertoire de travail
    if not uc_datas:
        import sys
        for path in sys.path:
            uc_candidate = os.path.join(path, 'undetected_chromedriver')
            if os.path.exists(uc_candidate):
                uc_datas = [(uc_candidate, 'undetected_chromedriver')]
                logger.info(f"undetected_chromedriver trouvé dans sys.path: {uc_candidate}")
                break

project_dir = os.path.dirname(os.path.abspath(SPEC))

datas = [
    (os.path.join(project_dir, 'bot'), 'bot'),
    (os.path.join(project_dir, 'AVIS'), 'AVIS'),
    (os.path.join(project_dir, 'config.yaml'), '.'),
    (os.path.join(project_dir, '.env'), '.'),
] + yaml_datas + uc_datas

binaries = yaml_binaries + uc_binaries
hiddenimports = [
    'selenium', 'selenium.webdriver', 'selenium.webdriver.common.by', 'selenium.webdriver.common.keys', 
    'selenium.webdriver.remote.webelement', 'selenium.webdriver.support', 'selenium.webdriver.support.ui',
    'selenium.webdriver.support.expected_conditions', 'selenium.webdriver.common.action_chains',
    'undetected_chromedriver', 'selenium_stealth', 
    'tkinter', 'yaml', '_yaml',
    'dotenv', 'python_dotenv', 'psutil', 'dateutil',
    'win10toast',  # Pour notifications (#21)
    'matplotlib', 'matplotlib.pyplot', 'matplotlib.backends', 'matplotlib.backends.backend_tkagg',  # Pour graphiques (#22)
    'pystray', 'PIL', 'PIL.Image', 'PIL.ImageDraw',  # Pour tray icon (#3)
    'requests',  # Pour notifications Discord (#5)
]

# Collecter les sous-modules yaml automatiquement
try:
    yaml_hidden = collect_submodules('yaml')
    hiddenimports += yaml_hidden
except:
    pass

# Collecter les sous-modules undetected_chromedriver automatiquement
try:
    uc_hidden = collect_submodules('undetected_chromedriver')
    hiddenimports += uc_hidden
except:
    pass

# Collecter tous les modules avec collect_all pour inclusion complète
tmp_ret = collect_all('selenium')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('undetected_chromedriver')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('selenium_stealth')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

# Collecter psutil
try:
    tmp_ret = collect_all('psutil')
    datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
except:
    pass

# Collecter dateutil
try:
    tmp_ret = collect_all('dateutil')
    datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
except:
    pass

# Collecter matplotlib
try:
    tmp_ret = collect_all('matplotlib')
    datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
except:
    pass

# Collecter win10toast
try:
    tmp_ret = collect_all('win10toast')
    datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
except:
    pass

# Collecter dotenv
try:
    tmp_ret = collect_all('dotenv')
    datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
except:
    pass

# Collecter pystray (#3)
try:
    tmp_ret = collect_all('pystray')
    datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
except:
    pass

# Collecter Pillow (#3)
try:
    tmp_ret = collect_all('PIL')
    datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
except:
    pass


a = Analysis(
    ['gui.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=['hooks'],  # Ajouter le dossier hooks
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
    name='MedalBot_Main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # Désactivé pour éviter les problèmes de compression
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
