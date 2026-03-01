# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for TaskMaster - Single EXE Mode

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Collect all data files for cffi and pycparser
datas = []
datas += [('templates', 'templates')]
datas += [('static', 'static')]
datas += [('mainfont.ttf', '.')]
datas += [('telegram_config.json', '.')]
datas += collect_data_files('cffi')
datas += collect_data_files('pycparser')

# Collect all submodules
hiddenimports = []
hiddenimports += ['flask', 'webview', 'werkzeug', 'pywebview']
hiddenimports += ['pywebview.platforms.winforms', 'pywebview.platforms.edgechromium']
hiddenimports += collect_submodules('cffi')
hiddenimports += collect_submodules('pycparser')
hiddenimports += ['pythonnet', 'clr', 'clr_loader']

block_cipher = None

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['test', 'tests', 'pytest', '_pytest', 'unittest', 'pydoc', 'doctest', 'tkinter', 'matplotlib', 'numpy', 'pandas',
              'PySide6', 'black', 'jedi', 'parso', 'nbformat'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='TaskMaster',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='taskmaster.ico',
)
