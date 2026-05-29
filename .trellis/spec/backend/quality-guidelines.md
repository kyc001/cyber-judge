# Quality Guidelines

> Code quality standards for backend development.

---

## Overview

<!--
Document your project's quality standards here.

Questions to answer:
- What patterns are forbidden?
- What linting rules do you enforce?
- What are your testing requirements?
- What code review standards apply?
-->

(To be filled by the team)

---

## Forbidden Patterns

<!-- Patterns that should never be used and why -->

(To be filled by the team)

---

## Required Patterns

<!-- Patterns that must always be used -->

(To be filled by the team)

---

## Testing Requirements

<!-- What level of testing is expected -->

(To be filled by the team)

---

## Code Review Checklist

<!-- What reviewers should check -->

(To be filled by the team)

---

## Scenario: Desktop Packaging Runtime

### 1. Scope / Trigger

- Trigger: backend or desktop changes that package FastAPI, `frontend/dist`, or
  `backend/wechat_decrypt` into `CyberJudgeDesktop.exe`.
- The packaged app runs from a PyInstaller temporary bundle directory, while
  user data must persist outside that directory.

### 2. Signatures

- Source launcher:
  `pixi run --manifest-path backend\pixi.toml python desktop\cyber_judge_desktop.py --no-webview`
- Windows package:
  `desktop\build-windows.bat`
- PyInstaller invocation:
  `pixi run --manifest-path backend\pixi.toml pyinstaller --noconfirm desktop\CyberJudgeDesktop.spec`
- Hidden script dispatch:
  `CyberJudgeDesktop.exe main.py <wechat_decrypt command>`

### 3. Contracts

- `CYBER_JUDGE_FRONTEND_DIST`: optional explicit `frontend/dist` path. Backend
  must serve `index.html`, `/assets/*`, and SPA routes from this path when it
  exists.
- `WECHAT_DECRYPT_CODE_DIR`: read-only bundled source directory containing
  `wechat_decrypt` scripts.
- `WECHAT_DECRYPT_PROJECT_DIR`: writable runtime directory for generated
  `config.json`, keys, decrypted DBs, and export state.
- `WECHAT_DECRYPT_APP_DIR`: passed to `wechat_decrypt.config` so relative
  config paths resolve under the writable runtime directory.
- `WECHAT_EXPORTED_CHATS_DIR`: writable exported-chat sample directory.
- `CYBER_JUDGE_SCRIPT_RUNNER`: optional runner for subprocess script dispatch;
  packaged mode uses `sys.executable`.

### 4. Validation & Error Matrix

- `frontend/dist/index.html` missing -> backend `/` returns 404 with a clear
  missing-assets message.
- Unknown `/api/*` route -> 404 API error, never the React SPA shell.
- `WECHAT_DECRYPT_CODE_DIR` missing -> WeChat prepare/list raises a missing
  module/project error.
- WeChat not running or admin permission missing -> prepare command returns a
  user-facing failure with the command output tail.
- PyInstaller hidden import missing -> packaged health check fails and the spec
  must add the explicit hidden import.

### 5. Good/Base/Bad Cases

- Good: packaged exe serves `/`, `/assets/*`, `/api/health`, and hidden
  `main.py status` reports a config path under `%LOCALAPPDATA%` or the
  configured `CYBER_JUDGE_APP_DATA`.
- Base: source launcher serves the same app after `npm run build`.
- Bad: `config.json`, `all_keys.json`, `decrypted/`, `exported_chats/`, or
  `wxwork_decrypted/` are bundled into the exe or written to `_MEIPASS`.

### 6. Tests Required

- `npm run build` from the repo root.
- `pixi run --manifest-path backend\pixi.toml python -m py_compile ...` for
  changed backend and desktop launcher files.
- Source launcher health check: start on a test port, assert `/api/health` 200,
  `/` 200 HTML, and unknown `/api/*` 404.
- Packaged exe health check with the same assertions.
- Packaged script dispatch check: run `CyberJudgeDesktop.exe main.py status`
  with a temporary `CYBER_JUDGE_APP_DATA` and assert the reported config path is
  under that runtime directory.

### 7. Wrong vs Correct

#### Wrong

```python
os.environ.setdefault("WECHAT_DECRYPT_PROJECT_DIR", str(backend_dir / "wechat_decrypt"))
```

This writes user config, keys, and decrypted databases into the bundled code
directory. In PyInstaller one-file mode, that may be a temporary `_MEIPASS`
directory.

#### Correct

```python
wechat_runtime_dir = data_dir / "wechat_decrypt"
os.environ.setdefault("WECHAT_DECRYPT_CODE_DIR", str(backend_dir / "wechat_decrypt"))
os.environ.setdefault("WECHAT_DECRYPT_PROJECT_DIR", str(wechat_runtime_dir))
os.environ.setdefault("WECHAT_DECRYPT_APP_DIR", str(wechat_runtime_dir))
```

Bundled code stays read-only; user data stays in the persistent app data
directory.
