#!/usr/bin/env node
/**
 * Pre-flight check for capacitor.config.json.
 *
 * Runs before `cap sync` / `cap:sync` to ensure the config is valid and
 * androidScheme is "https" (required for Mixed Content and OAuth).
 * Exit 1 on failure so the CI / npm script aborts early.
 */
import { readFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const configPath = resolve(__dirname, "../capacitor.config.json");

let raw;
try {
  raw = readFileSync(configPath, "utf-8");
} catch {
  console.error(`[check-capacitor-config] capacitor.config.json not found at ${configPath}`);
  process.exit(1);
}

let config;
try {
  config = JSON.parse(raw);
} catch (err) {
  console.error(`[check-capacitor-config] Invalid JSON in capacitor.config.json: ${err.message}`);
  process.exit(1);
}

const issues = [];

if (!config.appId) {
  issues.push("appId is missing");
}

if (!config.webDir) {
  issues.push("webDir is missing");
}

if (config.server?.androidScheme !== "https") {
  issues.push(
    `androidScheme must be "https" (found "${config.server?.androidScheme ?? "undefined"}"). ` +
      "HTTPS is required for OAuth popups and Mixed Content on Android."
  );
}

if (issues.length > 0) {
  console.error("[check-capacitor-config] Validation failed:");
  for (const issue of issues) {
    console.error(`  - ${issue}`);
  }
  process.exit(1);
}

console.log("[check-capacitor-config] OK");
