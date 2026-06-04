# PyInstaller spec — SiteSpider 本機桌面版
# 建置：見 scripts/build-desktop-mac.sh / build-desktop-win.ps1

import sys
from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent
PKG = ROOT / "sitespider"

block_cipher = None

datas = [
    (str(PKG / "ui"), "sitespider/ui"),
]

hiddenimports = [
    "webview",
    "sitespider.server",
    "sitespider.desktop_launcher",
    "sitespider.desktop_webview",
    "sitespider.crawler",
    "sitespider.report",
    "sitespider.job_store",
    "sitespider.usage",
    "sitespider.plans",
    "sitespider.lighthouse_runner",
    "sitespider.gsc_inspection",
    "email.mime.text",
]

a = Analysis(
    [str(PKG / "desktop_launcher.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter"],
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
    name="SiteSpider",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# macOS：取消註解以下區塊並註解上方單檔 EXE，可產出 SiteSpider.app
# coll = COLLECT(
#     exe,
#     a.binaries,
#     a.zipfiles,
#     a.datas,
#     strip=False,
#     upx=False,
#     upx_exclude=[],
#     name="SiteSpider",
# )
# app = BUNDLE(
#     coll,
#     name="SiteSpider.app",
#     icon=None,
#     bundle_identifier="app.sitespider.desktop",
#     info_plist={
#         "CFBundleDisplayName": "SiteSpider",
#         "CFBundleShortVersionString": "1.24.0",
#         "NSHighResolutionCapable": True,
#     },
# )
