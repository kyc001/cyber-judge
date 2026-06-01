# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


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

hiddenimports = [
    "uvicorn",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
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
    "wave",
    "export_all_chats",
    "mcp_server",
    "chat_export_helpers",
    "config",
    "decode_image",
    "key_utils",
]

excludes = [
    "mcp",
    "typer",
    "rich",
    "rich_toolkit",
    "pydantic_settings",
    "jsonschema",
    "jsonschema_specifications",
    "referencing",
    "httpx_sse",
    "webview",
    "pythonnet",
    "clr",
    "clr_loader",
    "proxy_tools",
    "tkinter",
    "_tkinter",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.protocols.websockets.wsproto_impl",
    "uvicorn.supervisors",
    "uvicorn.supervisors.basereload",
    "uvicorn.supervisors.multiprocess",
    "uvicorn.supervisors.statreload",
    "uvicorn.supervisors.watchfilesreload",
    "uvicorn.workers",
    "watchfiles",
    "websockets",
    "fastapi.testclient",
    "starlette.testclient",
]


a = Analysis(
    [str(ROOT / "desktop" / "cyber_judge_desktop.py")],
    pathex=[str(ROOT), str(BACKEND), str(WECHAT_DECRYPT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="CyberJudgeDesktopLite",
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
