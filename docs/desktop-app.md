# Cyber Judge Desktop App

The desktop app is the recommended product direction for non-technical users. It packages the existing FastAPI backend, built React frontend, and bundled WeChat import adapter behind a double-clickable local app.

## Support Matrix

| Platform | Status | Notes |
| --- | --- | --- |
| Windows | Official first target | Best fit for the current WeChat decrypt and EXE distribution flow. |
| macOS | Future beta | Needs a polished permission, codesign, and sudo guidance flow. |
| Linux | Future developer mode | WeChat runtime and permission differences are too broad for the first public release. |

## Runtime Flow

1. Launch `CyberJudgeDesktop.exe`.
2. The launcher starts FastAPI on `127.0.0.1`.
3. FastAPI serves `frontend/dist` and all `/api/*` endpoints from the same local origin.
4. The launcher opens an embedded WebView when available, otherwise the default browser.
5. Users follow the existing Local WeChat import flow.

## Source-Mode Run

This project uses Pixi for the backend runtime. Do not run the desktop backend with a random global Python environment.

Build frontend assets first:

```powershell
npm run build
```

Run the desktop launcher in browser mode:

```powershell
pixi run --manifest-path backend\pixi.toml python desktop\cyber_judge_desktop.py --no-webview
```

If `pywebview` is added to the Pixi environment later, test the embedded window with:

```powershell
pixi run --manifest-path backend\pixi.toml python desktop\cyber_judge_desktop.py
```

## Windows Build

```powershell
desktop\build-windows.bat
```

The build script uses:

```powershell
pixi run --manifest-path backend\pixi.toml pyinstaller --noconfirm desktop\CyberJudgeDesktop.spec
```

The PyInstaller spec uses a whitelist for `backend/wechat_decrypt` files. It must not package local private data such as `config.json`, `all_keys.json`, `decrypted/`, `exported_chats/`, or `wxwork_decrypted/`.

Output:

```text
dist\CyberJudgeDesktop.exe
```

## Environment

The launcher sets these defaults unless already provided:

- `DATABASE_PATH` under the user's local app data directory
- `WECHAT_IMPORT_OUTPUT_DIR` under the user's local app data directory
- `WECHAT_DECRYPT_CODE_DIR` to the bundled `backend/wechat_decrypt`
- `WECHAT_DECRYPT_PROJECT_DIR` and `WECHAT_DECRYPT_APP_DIR` under the user's local app data directory
- `WECHAT_EXPORTED_CHATS_DIR` under the user's local app data directory
- `CYBER_JUDGE_FRONTEND_DIST` to the built frontend directory
- `SHARE_BASE_URL` and `CORS_ORIGINS` to the local desktop origin

LLM provider settings still come from the existing backend environment variables or `.env` file.

## Notes

- Manual JSON upload remains available as an advanced fallback.
- The first desktop milestone does not redesign the frontend import page.
- Unsigned Windows executables that inspect process memory may trigger antivirus warnings; signing and installer work are future release tasks.
