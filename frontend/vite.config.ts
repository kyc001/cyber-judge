import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { spawn, type ChildProcess } from "child_process";
import { existsSync } from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const backendDir = path.resolve(__dirname, "..", "backend");

function autoStartBackend(): any {
  let backend: ChildProcess | null = null;

  function startBackend(pythonBin: string) {
    console.log("  [auto-start] Using python:", pythonBin);
    backend = spawn(pythonBin, ["main.py"], {
      cwd: backendDir,
      stdio: "pipe",
      env: { ...process.env, PYTHONUNBUFFERED: "1" },
    });

    backend.stdout?.on("data", (d: Buffer) => {
      const msg = d.toString().trim();
      if (msg) console.log("  [backend]", msg);
    });
    backend.stderr?.on("data", (d: Buffer) => {
      const msg = d.toString().trim();
      if (msg) console.log("  [backend]", msg);
    });
    backend.on("error", (err) => {
      console.error("  [auto-start] Backend spawn error:", err.message);
      console.error("  [auto-start] Start backend manually: cd backend && python main.py");
    });
    backend.on("exit", (code: number | null) => {
      if (code !== null && code !== 0 && backend) {
        console.error(`  [auto-start] Backend exited (code ${code}), restarting...`);
        startBackend(pythonBin);
      }
    });
  }

  return {
    name: "auto-start-backend",
    configureServer() {
      console.log("[auto-start] Starting backend...");
      const venvPython = path.join(backendDir, "venv", "Scripts", "python.exe");
      const pythonBin = existsSync(venvPython) ? venvPython : "python";
      startBackend(pythonBin);
    },
    closeBundle() {
      if (backend) {
        console.log("[auto-start] Stopping backend...");
        backend.kill();
        backend = null;
      }
    },
  };
}

export default defineConfig({
  plugins: [autoStartBackend(), react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
