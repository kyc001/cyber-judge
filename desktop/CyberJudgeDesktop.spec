# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_all


ROOT = Path(SPECPATH).resolve().parent
BACKEND = ROOT / "backend"
WECHAT_DECRYPT = BACKEND / "wechat_decrypt"
FRONTEND_DIST = ROOT / "frontend" / "dist"

datas = [
    (str(FRONTEND_DIST), "frontend/dist"),
]

backend_files = [
    "main.py",
    "database.py",
    "fallback.py",
    "llm_service.py",
    "models.py",
    "parser.py",
    "prompts.py",
    "stats.py",
    "stats_extra.py",
    "wechat_importer.py",
]

for file_name in backend_files:
    datas.append((str(BACKEND / file_name), "backend"))

wechat_decrypt_files = [
    "batch_decrypt_images.py",
    "chat_export_helpers.py",
    "cleanup.py",
    "config.example.json",
    "config.py",
    "decode_image.py",
    "decode_transfer.py",
    "decrypt_db.py",
    "decrypt_sns.py",
    "decrypt_wxwork_db.py",
    "export_all_chats.py",
    "export_chat.py",
    "export_messages.py",
    "export_sns.py",
    "export_wxwork_messages.py",
    "find_all_keys.py",
    "find_all_keys_linux.py",
    "find_all_keys_windows.py",
    "find_image_key.py",
    "find_image_key_monitor.py",
    "find_wxwork_keys.py",
    "key_scan_common.py",
    "key_utils.py",
    "main.py",
    "mcp_server.py",
    "monitor.py",
    "monitor_web.py",
    "transcribe_chat.py",
    "voice_to_mp3.py",
    "wechat_decrypt_launcher.py",
    "wxwork_crypto.py",
]

for file_name in wechat_decrypt_files:
    datas.append((str(WECHAT_DECRYPT / file_name), "backend/wechat_decrypt"))

binaries = []
hiddenimports = [
    "uvicorn",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "sqlite3",
    "_sqlite3",
    "fastapi",
    "starlette",
    "pydantic",
    "jieba",
    "dotenv",
    "httpx",
    "Crypto",
    "Crypto.Cipher",
    "Crypto.Cipher.AES",
    "zstandard",
    "mcp",
    "wave",
    "export_all_chats",
    "mcp_server",
    "chat_export_helpers",
    "config",
    "decode_image",
    "key_utils",
    # pywebview Windows (EdgeChromium) backend chain
    "clr",
    "webview.platforms.edgechromium",
    "webview.platforms.winforms",
    "webview.platforms.mshtml",
    "proxy_tools",
]

# webview/pythonnet/clr_loader ship native DLLs (WebView2, WebBrowserInterop,
# Python.Runtime) that PyInstaller only bundles via collect_all; without them
# `import webview` fails in the frozen exe and the launcher silently falls back
# to the browser instead of showing the embedded GUI window.
for package in (
    "jieba",
    "uvicorn",
    "fastapi",
    "starlette",
    "pydantic",
    "webview",
    "pythonnet",
    "clr_loader",
):
    collected = collect_all(package)
    datas += collected[0]
    binaries += collected[1]
    hiddenimports += collected[2]


a = Analysis(
    [str(ROOT / "desktop" / "cyber_judge_desktop.py")],
    pathex=[str(ROOT), str(BACKEND), str(WECHAT_DECRYPT)],
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
    name="CyberJudgeDesktop",
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
