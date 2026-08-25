#!/usr/bin/env node
/**
 * MOB-P0-001 / MOB-P0-002: Pre-flight check de Capacitor.
 *
 * Valida (antes de `cap sync` / build):
 *   1. Que capacitor.config.ts existe (fuente de verdad; el .json no se usa).
 *   2. Que no haya secretos reales commiteados en git.
 *   3. Que las variables de entorno móvil obligatorias estén definidas
 *      cuando la autenticación está activa.
 *
 * CI debug/smoke builds no necesitan credenciales Google: se ejecutan en
 * modo AUTH_DISABLED para validar el empaquetado sin introducir secretos.
 * Los builds de release por tag siguen requiriendo las credenciales reales.
 */
import { readFileSync, existsSync } from "node:fs";
import { execSync } from "node:child_process";
import { resolve, dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const rootDir = resolve(__dirname, "..");
const androidAppDir = join(rootDir, "android", "app");

const issues = [];
const warnings = [];

const configTsPath = join(rootDir, "capacitor.config.ts");
if (!existsSync(configTsPath)) {
  issues.push("capacitor.config.ts no existe. Es la fuente de verdad de la config de Capacitor.");
}

try {
  const tracked = execSync(
    "git ls-files --error-unmatch android/app/google-services.json",
    { cwd: androidAppDir, stdio: ["ignore", "pipe", "ignore"] }
  ).toString();
  if (tracked.trim()) {
    issues.push(
      "SEC-001: android/app/google-services.json está commiteado en git. " +
        "Ejecuta: git rm --cached android/app/google-services.json"
    );
  }
} catch {
  // No trackeado → OK
}

const configJsonPath = join(rootDir, "capacitor.config.json");
if (existsSync(configJsonPath)) {
  const content = readFileSync(configJsonPath, "utf-8");
  const idPattern = /\d{10,}-[a-z0-9]{20,}\.apps\.googleusercontent\.com/;
  if (idPattern.test(content)) {
    issues.push(
      "SEC-001: capacitor.config.json contiene Google Client IDs hardcodeados. " +
        "Elimínalo: usa capacitor.config.ts que lee de env vars."
    );
  } else {
    warnings.push(
      "capacitor.config.json existe pero no debería committearse. " +
        "Considera eliminarlo y usar solo capacitor.config.ts."
    );
  }
}

const googleClientsPath = join(rootDir, "src", "app", "config", "google-clients.ts");
if (existsSync(googleClientsPath)) {
  const content = readFileSync(googleClientsPath, "utf-8");
  const idPattern = /\d{10,}-[a-z0-9]{20,}\.apps\.googleusercontent\.com/;
  if (idPattern.test(content)) {
    issues.push(
      "SEC-001: google-clients.ts contiene Google Client IDs hardcodeados. " +
        "Elimínalos: los valores deben venir solo de env vars (.env.local)."
    );
  }
}

function readDotEnv() {
  const envPath = join(rootDir, ".env.local");
  const result = {};
  if (!existsSync(envPath)) return result;
  for (const line of readFileSync(envPath, "utf-8").split("\n")) {
    const m = line.match(/^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.*)\s*$/);
    if (m) result[m[1]] = m[2].replace(/^["']|["']$/g, "");
  }
  return result;
}

const env = { ...process.env, ...readDotEnv() };
const ref = env.GITHUB_REF ?? "";
const isReleaseTag = ref.startsWith("refs/tags/v");
const isCiDebugBuild = env.CI === "true" && !isReleaseTag;
const authDisabled =
  (env.NEXT_PUBLIC_AUTH_DISABLED ?? "").toLowerCase() === "true" || isCiDebugBuild;

const REQUIRED_ALWAYS = ["NEXT_PUBLIC_API_URL"];
const REQUIRED_IF_AUTH = [
  "NEXT_PUBLIC_GOOGLE_WEB_CLIENT_ID",
  "NEXT_PUBLIC_GOOGLE_ANDROID_CLIENT_ID",
];

for (const varName of REQUIRED_ALWAYS) {
  if (!env[varName] && !isCiDebugBuild) {
    issues.push(`${varName} no está definida en .env.local (ver frontend/.env.example).`);
  }
}

if (!authDisabled) {
  for (const varName of REQUIRED_IF_AUTH) {
    const value = env[varName] ?? "";
    if (!value || value.includes("YOUR_") || value.includes("placeholder")) {
      issues.push(
        `${varName} no está definida en .env.local. Requerida para login Google ` +
          `(NEXT_PUBLIC_AUTH_DISABLED no es true). Ver frontend/.env.example.`
      );
    }
  }
}

for (const w of warnings) console.warn(`WARN: ${w}`);
if (issues.length > 0) {
  console.error("❌ check-capacitor-config FAILED");
  for (const issue of issues) console.error(`  - ${issue}`);
  process.exit(1);
}

if (isCiDebugBuild) {
  console.log("ℹ️ CI debug build: autenticación Google deshabilitada para el pre-flight.");
}
console.log("✅ check-capacitor-config PASSED");
process.exit(0);
