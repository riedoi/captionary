# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('static', 'static'), ('/Users/ismosh/Documents/vidscribe/venv/lib/python3.13/site-packages/faster_whisper/assets', 'faster_whisper/assets')]
binaries = [('ffmpeg', '.')]
hiddenimports = ['uvicorn.logging', 'uvicorn.loops', 'uvicorn.loops.auto', 'uvicorn.protocols', 'uvicorn.protocols.http', 'uvicorn.protocols.http.auto', 'uvicorn.lifespan', 'uvicorn.lifespan.on', 'engineio.async_drivers.asgi', 'faster_whisper', 'webview', 'clr', 'webview.platforms.cocoa', 'python-multipart']
tmp_ret = collect_all('faster_whisper')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['gui_launcher.py'],
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
    [],
    exclude_binaries=True,
    name='Captionary',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Captionary',
)
app = BUNDLE(
    coll,
    name='Captionary.app',
    icon=None,
    bundle_identifier='com.riedoi.captionary',
)
