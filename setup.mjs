import { spawnSync } from "child_process";
import { existsSync } from "fs";
import { join } from "path";
import { platform } from "os";

const CWD = import.meta.dirname;
const BACKEND = join(CWD, "backend");
const FRONTEND = join(CWD, "frontend");
const isWin = platform() === "win32";

const pythonBin = join(BACKEND, "venv", "Scripts", "python.exe");
const pipBin = join(BACKEND, "venv", "Scripts", "pip.exe");

function run(cmd, args, opts) {
  console.log(`  → ${cmd} ${args.join(" ")}`);
  const r = spawnSync(cmd, args, {
    stdio: "inherit",
    shell: true,
    ...opts,
  });
  if (r.status !== 0) throw new Error(`${cmd} failed`);
}

console.log("=== Cyber Judge Setup ===\n");

// 1. Frontend
console.log("[1/3] Installing frontend dependencies...");
run("npm", ["install"], { cwd: FRONTEND });

// 2. Python venv
console.log("\n[2/3] Setting up Python virtual environment...");
if (!existsSync(pythonBin)) {
  const py = isWin ? "python" : "python3";
  run(py, ["-m", "venv", "venv"], { cwd: BACKEND });
}
run(pipBin, ["install", "-r", "requirements.txt"], { cwd: BACKEND });

// 3. Verify
console.log("\n[3/3] Verifying...");
run("node", ["-e", "require('react')"], { cwd: FRONTEND });
run(pythonBin, ["-c", "import fastapi, uvicorn, httpx, jieba; print('backend OK')"], { cwd: BACKEND, shell: false });

console.log("\nSetup complete. Run: npm run dev");
