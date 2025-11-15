# Hook PyInstaller pour undetected_chromedriver
from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files
import os

datas = []
binaries = []
hiddenimports = []

try:
    # Essayer de collecter le module
    tmp_ret = collect_all('undetected_chromedriver')
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]
    
    # Ajouter les sous-modules
    hiddenimports += collect_submodules('undetected_chromedriver')
except:
    pass

# Ajouter les imports cachés spécifiques (même si le module n'est pas trouvé)
hiddenimports += [
    'undetected_chromedriver',
    'undetected_chromedriver.v2',
    'undetected_chromedriver.patcher',
]

