# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[('templates', 'templates'), ('mainfont.ttf', '.'), ('telegram_config.json', '.')],
    hiddenimports=['flask', 'webview', 'werkzeug', 'pywebview'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['test', 'tests', 'pytest', '_pytest', 'unittest', 'pydoc', 'doctest', 'tkinter', 'matplotlib', 'numpy', 'pandas'],
    noarchive=False,
    optimize=2,
)
pyz = PYZ(a.pure)

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
    icon=['taskmaster.ico'],
)
