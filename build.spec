# -*- mode: python ; coding: utf-8 -*-
import sys
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# Hidden imports that PyInstaller might miss
hiddenimports = [
    'sklearn.utils._cython_blas',
    'sklearn.utils._typedefs',
    'sklearn.neighbors._partition_nodes',
    'sklearn.tree._utils',
    'scipy.special.cython_special',
    'skimage.feature._hessian_det_appx',
    'skimage.draw',
    'monai.networks.nets',
    'monai.losses',
    'monai.utils',
    'pennylane', # Critical for QuantumLayer
    'pennylane_lightning',
    'email',
]

# Collect data for complex packages
datas = []
binaries = []

# Collect all from monai and pennylane
tmp_ret = collect_all('monai')
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

tmp_ret_pl = collect_all('pennylane')
datas += tmp_ret_pl[0]
binaries += tmp_ret_pl[1]
hiddenimports += tmp_ret_pl[2]

# Add Assets
datas += [('assets', 'assets')]

a = Analysis(
    ['app/main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'models', # Exclude models dir content
        'tkinter', 'tcl', 'dot', 'unittest', 'http', 'pydoc', 'pdb', 
        'IPython', 'jupyter', 'notebook', 'nbconvert', 'nbformat', 'jedi', 'parso',
        'matplotlib.tests', 'numpy.tests', 'scipy.tests', 'pandas.tests', 
        'torch.distributions', 'torch.testing', 'torch.utils.benchmark',
        'PyQt6', 'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets'
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
    [],
    exclude_binaries=True,
    name='NeuroSegPro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False, # Windowed mode (no console)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements=None,
    icon='assets/NeuroSeg_App_Icon.png'
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='NeuroSegPro',
)
