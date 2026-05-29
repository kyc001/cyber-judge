"""Desktop launcher for the local Cyber Judge app."""

from __future__ import annotations

import argparse
import atexit
import os
import runpy
import socket
import sys
import threading
import time
import traceback
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path


APP_NAME = "Cyber Judge"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
_LOG_STREAMS = []
_STDOUT_IS_LOG = False


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _bundle_dir() -> Path:
    if _is_frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parents[1]


def _runtime_dir() -> Path:
    if _is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def _app_data_dir() -> Path:
    root = os.environ.get("CYBER_JUDGE_APP_DATA", "").strip()
    if root:
        path = Path(root)
    elif os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        path = Path(base) / "CyberJudge"
    else:
        path = Path.home() / ".cyber-judge"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _log_path() -> Path:
    return _app_data_dir() / "desktop.log"


def _ensure_standard_streams() -> None:
    global _STDOUT_IS_LOG
    if sys.stdout is None:
        stdout_log = _log_path().open("a", encoding="utf-8", buffering=1)
        sys.stdout = stdout_log
        _LOG_STREAMS.append(stdout_log)
        _STDOUT_IS_LOG = True
    if sys.stderr is None:
        stderr_log = _log_path().open("a", encoding="utf-8", buffering=1)
        sys.stderr = stderr_log
        _LOG_STREAMS.append(stderr_log)


def _log(message: str) -> None:
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}"
    if not _STDOUT_IS_LOG:
        print(line, flush=True)
    try:
        with _log_path().open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except OSError:
        pass


def _backend_dir() -> Path:
    return _bundle_dir() / "backend"


def _frontend_dist_dir() -> Path:
    candidates = [
        _bundle_dir() / "frontend" / "dist",
        _bundle_dir() / "frontend_dist",
        _runtime_dir() / "frontend" / "dist",
    ]
    for candidate in candidates:
        if (candidate / "index.html").exists():
            return candidate
    return candidates[0]


def _find_available_port(preferred: int) -> int:
    for port in [preferred, *range(preferred + 1, preferred + 50)]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((DEFAULT_HOST, port))
            except OSError:
                continue
            return port
    raise RuntimeError("No available local port found for Cyber Judge.")


def _configure_environment(host: str, port: int) -> None:
    data_dir = _app_data_dir()
    backend_dir = _backend_dir()
    wechat_runtime_dir = data_dir / "wechat_decrypt"
    wechat_runtime_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("HOST", host)
    os.environ["PORT"] = str(port)
    os.environ.setdefault("CYBER_JUDGE_DESKTOP", "1")
    if _is_frozen():
        os.environ.setdefault("CYBER_JUDGE_SCRIPT_RUNNER", sys.executable)
    os.environ.setdefault("CYBER_JUDGE_FRONTEND_DIST", str(_frontend_dist_dir()))
    os.environ.setdefault("DATABASE_PATH", str(data_dir / "data" / "cyber_judge.db"))
    os.environ.setdefault("WECHAT_IMPORT_OUTPUT_DIR", str(data_dir / "imported_chats"))
    os.environ.setdefault("WECHAT_DECRYPT_CODE_DIR", str(backend_dir / "wechat_decrypt"))
    os.environ.setdefault("WECHAT_DECRYPT_PROJECT_DIR", str(wechat_runtime_dir))
    os.environ.setdefault("WECHAT_DECRYPT_APP_DIR", str(wechat_runtime_dir))
    os.environ.setdefault("WECHAT_EXPORTED_CHATS_DIR", str(wechat_runtime_dir / "exported_chats"))
    os.environ.setdefault("SHARE_BASE_URL", f"http://{host}:{port}")
    os.environ.setdefault("CORS_ORIGINS", f"http://{host}:{port}")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    _log(f"bundle_dir={_bundle_dir()}")
    _log(f"runtime_dir={_runtime_dir()}")
    _log(f"frontend_dist={os.environ['CYBER_JUDGE_FRONTEND_DIST']}")
    _log(f"database_path={os.environ['DATABASE_PATH']}")
    _log(f"wechat_code_dir={os.environ['WECHAT_DECRYPT_CODE_DIR']}")
    _log(f"wechat_project_dir={os.environ['WECHAT_DECRYPT_PROJECT_DIR']}")


def _ensure_import_paths() -> None:
    backend_dir = _backend_dir()
    root_dir = _bundle_dir()
    wechat_dir = Path(os.environ.get("WECHAT_DECRYPT_CODE_DIR", str(backend_dir / "wechat_decrypt")))
    for path in (str(wechat_dir), str(backend_dir), str(root_dir)):
        if path not in sys.path:
            sys.path.insert(0, path)


def _configure_script_environment() -> None:
    data_dir = _app_data_dir()
    backend_dir = _backend_dir()
    wechat_runtime_dir = data_dir / "wechat_decrypt"
    wechat_runtime_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("CYBER_JUDGE_DESKTOP", "1")
    os.environ.setdefault("WECHAT_DECRYPT_CODE_DIR", str(backend_dir / "wechat_decrypt"))
    os.environ.setdefault("WECHAT_DECRYPT_PROJECT_DIR", str(wechat_runtime_dir))
    os.environ.setdefault("WECHAT_DECRYPT_APP_DIR", str(wechat_runtime_dir))
    os.environ.setdefault("WECHAT_EXPORTED_CHATS_DIR", str(wechat_runtime_dir / "exported_chats"))
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")


def _script_candidates(script_arg: str) -> list[Path]:
    script_path = Path(script_arg)
    candidates = [script_path]
    if not script_path.is_absolute():
        code_dir = Path(os.environ.get("WECHAT_DECRYPT_CODE_DIR", str(_backend_dir() / "wechat_decrypt")))
        candidates.extend([
            Path.cwd() / script_path,
            code_dir / script_path.name,
            _backend_dir() / script_path.name,
        ])
    return candidates


def _run_script_entrypoint() -> int:
    _ensure_standard_streams()
    _configure_script_environment()
    _ensure_import_paths()
    script_arg = sys.argv[1]
    for candidate in _script_candidates(script_arg):
        if candidate.exists():
            sys.argv = [str(candidate), *sys.argv[2:]]
            work_dir = os.environ.get("WECHAT_DECRYPT_APP_DIR", "").strip()
            os.chdir(work_dir or str(candidate.parent))
            runpy.run_path(str(candidate), run_name="__main__")
            return 0
    raise FileNotFoundError(f"Bundled script not found: {script_arg}")


def _start_backend(host: str, port: int):
    _ensure_import_paths()
    import uvicorn

    _log(f"starting backend on http://{host}:{port}")
    config = uvicorn.Config(
        "main:app",
        host=host,
        port=port,
        log_level=os.environ.get("CYBER_JUDGE_LOG_LEVEL", "info"),
        use_colors=False,
        reload=False,
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, name="cyber-judge-backend", daemon=True)
    thread.start()

    def stop_server() -> None:
        server.should_exit = True
        thread.join(timeout=5)

    atexit.register(stop_server)
    return server, thread


def _wait_until_ready(url: str, timeout_seconds: int = 45) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error = ""
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    _log(f"backend ready at {url}")
                    return
        except (OSError, urllib.error.URLError) as exc:
            last_error = str(exc)
        time.sleep(0.5)
    raise RuntimeError(f"Cyber Judge backend did not become ready: {last_error}")


def _open_webview(url: str) -> bool:
    try:
        import webview  # type: ignore
    except Exception:
        return False

    try:
        webview.create_window(APP_NAME, url, width=1240, height=860, min_size=(960, 640))
        webview.start()
        return True
    except Exception as exc:
        _log(f"WebView failed, opening browser instead: {exc}")
        return False


def _keep_alive_until_interrupted() -> None:
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        return


def _open_browser_with_control_window(url: str, *, show_control_window: bool) -> None:
    webbrowser.open(url)
    _log(f"Cyber Judge is running at {url}")

    if not show_control_window:
        _keep_alive_until_interrupted()
        return

    try:
        import tkinter as tk
        from tkinter import ttk
    except Exception as exc:
        _log(f"Control window unavailable: {exc}")
        _keep_alive_until_interrupted()
        return

    root = tk.Tk()
    root.title(APP_NAME)
    root.geometry("420x180")
    root.resizable(False, False)

    frame = ttk.Frame(root, padding=18)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text="Cyber Judge is running in your browser.", font=("", 11, "bold")).pack(anchor="w")
    ttk.Label(frame, text="Close this window to stop the local desktop service.", wraplength=360).pack(anchor="w", pady=(8, 14))
    ttk.Button(frame, text="Open Browser", command=lambda: webbrowser.open(url)).pack(side="left")
    ttk.Button(frame, text="Stop", command=root.destroy).pack(side="right")
    root.mainloop()


def _open_ui(url: str, *, use_webview: bool, show_control_window: bool) -> None:
    if use_webview and _open_webview(url):
        return
    _open_browser_with_control_window(url, show_control_window=show_control_window)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launch Cyber Judge desktop app.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--no-webview", action="store_true", help="Open in the default browser instead of an embedded window.")
    parser.add_argument("--no-control-window", action="store_true", help="Do not show the browser fallback control window.")
    parser.add_argument("--timeout", type=int, default=45, help="Seconds to wait for the backend to become ready.")
    return parser.parse_args()


def main() -> int:
    _ensure_standard_streams()
    args = parse_args()
    port = _find_available_port(args.port)
    _configure_environment(args.host, port)
    _start_backend(args.host, port)

    base_url = f"http://{args.host}:{port}"
    _wait_until_ready(f"{base_url}/api/health", timeout_seconds=args.timeout)
    _open_ui(base_url, use_webview=not args.no_webview, show_control_window=not args.no_control_window)
    return 0


def _show_fatal_error(message: str) -> None:
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(APP_NAME, f"{message}\n\nLog: {_log_path()}")
        root.destroy()
    except Exception:
        pass


if __name__ == "__main__":
    try:
        if len(sys.argv) > 1 and sys.argv[1].lower().endswith(".py"):
            raise SystemExit(_run_script_entrypoint())
        raise SystemExit(main())
    except Exception as exc:
        _log("fatal error:")
        _log(traceback.format_exc())
        _show_fatal_error(str(exc))
        raise
