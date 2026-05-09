#!/usr/bin/env node

const { spawnSync } = require("node:child_process");
const path = require("node:path");

const projectRoot = path.resolve(__dirname, "..");
const args = ["-m", "openshow", ...process.argv.slice(2)];
const env = {
  ...process.env,
  PYTHONPATH: [projectRoot, process.env.PYTHONPATH].filter(Boolean).join(path.delimiter),
};
const candidates = process.platform === "win32" ? ["python", "py"] : ["python3", "python"];

let lastError = null;

for (const command of candidates) {
  const result = spawnSync(command, args, { env, stdio: "inherit" });

  if (result.error && result.error.code === "ENOENT") {
    lastError = result.error;
    continue;
  }

  if (result.error) {
    console.error(`openshow: failed to start ${command}: ${result.error.message}`);
    process.exit(1);
  }

  if (result.signal) {
    process.kill(process.pid, result.signal);
  }

  process.exit(result.status ?? 0);
}

console.error("openshow: Python 3 is required but was not found on PATH.");
if (lastError) {
  console.error(`openshow: last error: ${lastError.message}`);
}
process.exit(1);
