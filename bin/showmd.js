#!/usr/bin/env node

const { spawnSync } = require("node:child_process");
const path = require("node:path");

const script = path.resolve(__dirname, "..", "obsidian_cli.py");
const args = [script, ...process.argv.slice(2)];
const candidates = process.platform === "win32" ? ["python", "py"] : ["python3", "python"];

let lastError = null;

for (const command of candidates) {
  const result = spawnSync(command, args, { stdio: "inherit" });

  if (result.error && result.error.code === "ENOENT") {
    lastError = result.error;
    continue;
  }

  if (result.error) {
    console.error(`showmd: failed to start ${command}: ${result.error.message}`);
    process.exit(1);
  }

  if (result.signal) {
    process.kill(process.pid, result.signal);
  }

  process.exit(result.status ?? 0);
}

console.error("showmd: Python 3 is required but was not found on PATH.");
if (lastError) {
  console.error(`showmd: last error: ${lastError.message}`);
}
process.exit(1);
