import { spawnSync } from "child_process";
import { existsSync, rmSync } from "fs";
import { join } from "path";
import { platform } from "os";

const CWD = import.meta.dirname;
const BACKEND = join(CWD, "backend");
const FRONTEND = join(CWD, "frontend");
const WECHAT_DECRYPT = join(BACKEND, "wechat_decrypt");
const VENV = join(BACKEND, "venv");
const isWin = platform() === "win32";

const venvPython = isWin
  ? join(VENV, "Scripts", "python.exe")
  : join(VENV, "bin", "python");

function printable(cmd, args) {
  return [cmd, ...args].join(" ");
}

function run(cmd, args, opts = {}) {
  console.log(`  -> ${printable(cmd, args)}`);
  const r = spawnSync(cmd, args, {
    stdio: "inherit",
    shell: true,
    ...opts,
  });
  if (r.status !== 0) throw new Error(`${cmd} failed`);
}

function capture(cmd, args, opts = {}) {
  return spawnSync(cmd, args, {
    encoding: "utf8",
    shell: false,
    ...opts,
  });
}

function pythonVersion(cmd, args = []) {
  const code = [
    "import sys",
    "v=sys.version_info",
    "print(f'{v.major}.{v.minor}.{v.micro}')",
    "raise SystemExit(0 if (v.major, v.minor) >= (3, 11) and (v.major, v.minor) <= (3, 13) else 2)",
  ].join("; ");
  const r = capture(cmd, [...args, "-c", code]);
  return {
    ok: r.status === 0,
    found: r.status === 0 || r.status === 2,
    version: (r.stdout || "").trim(),
  };
}

function findPython() {
  const candidates = isWin
    ? [
        { cmd: "py", args: ["-3.12"] },
        { cmd: "py", args: ["-3.11"] },
        { cmd: "py", args: ["-3.13"] },
        { cmd: "python", args: [] },
        { cmd: "python3", args: [] },
      ]
    : [
        { cmd: "python3.12", args: [] },
        { cmd: "python3.11", args: [] },
        { cmd: "python3.13", args: [] },
        { cmd: "python3", args: [] },
        { cmd: "python", args: [] },
      ];
  if (process.env.PYTHON) {
    candidates.unshift({ cmd: process.env.PYTHON, args: [] });
  }

  const seen = [];
  for (const candidate of candidates) {
    const version = pythonVersion(candidate.cmd, candidate.args);
    if (!version.found) continue;
    seen.push(`${printable(candidate.cmd, candidate.args)} (${version.version || "unknown"})`);
    if (version.ok) {
      console.log(`  using Python ${version.version}: ${printable(candidate.cmd, candidate.args)}`);
      return candidate;
    }
  }

  throw new Error(
    [
      "No compatible Python was found.",
      "Install 64-bit Python 3.11, 3.12, or 3.13, then rerun npm run setup.",
      "Python 3.14 or newer may force pydantic-core to compile from source and requires MSVC.",
      seen.length ? `Detected: ${seen.join(", ")}` : "Detected: none",
    ].join("\n")
  );
}

function ensureVenv() {
  if (existsSync(venvPython)) {
    const version = pythonVersion(venvPython);
    if (version.ok) {
      console.log(`  existing venv Python ${version.version} is compatible`);
      return;
    }
    console.log(`  existing venv Python ${version.version || "unknown"} is not compatible; rebuilding backend/venv`);
    rmSync(VENV, { recursive: true, force: true });
  }

  const python = findPython();
  run(python.cmd, [...python.args, "-m", "venv", "venv"], { cwd: BACKEND });
}

console.log("=== Cyber Judge Setup ===\n");

console.log("[1/3] Installing frontend dependencies...");
run("npm", ["install"], { cwd: FRONTEND });

console.log("\n[2/3] Setting up Python virtual environment...");
ensureVenv();
run(venvPython, ["-m", "pip", "install", "--upgrade", "pip"], { cwd: BACKEND, shell: false });
run(
  venvPython,
  ["-m", "pip", "install", "--only-binary", "pydantic-core", "-r", "requirements.txt"],
  { cwd: BACKEND, shell: false }
);

console.log("\n[3/3] Verifying...");
run("node", ["-e", "require('react')"], { cwd: FRONTEND });
if (!existsSync(join(WECHAT_DECRYPT, "export_all_chats.py"))) {
  throw new Error("bundled wechat_decrypt module is missing");
}
run(
  venvPython,
  ["-c", "import fastapi, uvicorn, httpx, jieba, mcp, Crypto, zstandard; print('backend OK')"],
  { cwd: BACKEND, shell: false }
);

console.log("\nSetup complete. Run: npm run dev");
