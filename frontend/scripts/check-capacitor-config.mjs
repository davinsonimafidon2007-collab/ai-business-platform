#!/usr/bin/env node
/**
 * MOB-P0-001 / MOB-P0-002: Pre-flight check de Capacitor.
 *
 * Valida (antes de `cap sync` / build):
 *   1. Que capacitor.config.ts existe (fuente de verdad; el .json no se usa).
 *   2. Que no haya secretos reales commiteados en git
 *      (google-services.json, client IDs hardcodeados en capacitor.config.*,
 *       fallbacks en google-clients.ts).
 *   3. Que las variables de entorno móvil obligatorias estén definidas en
 *      .env.local cuando la autenticación está activa (AUTH_DISABLED=false).
 *
 * Exit 1 on failure so CI / npm scripts abort early.
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

// ---------------------------------------------------------------------------
// 1. Fuente de verdad: capacitor.config.ts (el .json ya no se commitea)
// ---------------------------------------------------------------------------
const configTsPath = join(rootDir, "capacitor.config.ts");
if (!existsSync(configTsPath)) {
  issues.push("capacitor.config.ts no existe. Es la fuente de verdad de la config de Capacitor.");
}

// ---------------------------------------------------------------------------
// 2. Secretos expuestos
// ---------------------------------------------------------------------------
// 2.1 google-services.json NO debe estar commiteado en git
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

// 2.2 capacitor.config.json NO debe existir (solo el .ts) ni tener IDs hardcodeados
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

// 2.3 google-clients.ts no debe tener client IDs hardcodeados como fallback
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

// ---------------------------------------------------------------------------
// 3. Variables de entorno móvil obligatorias (MOB-P0-002)
// ---------------------------------------------------------------------------
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
const authDisabled = (env.NEXT_PUBLIC_AUTH_DISABLED ?? "").toLowerCase() === "true";

const REQUIRED_ALWAYS = ["NEXT_PUBLIC_API_URL"];
const REQUIRED_IF_AUTH = [
  "NEXT_PUBLIC_GOOGLE_WEB_CLIENT_ID",
  "NEXT_PUBLIC_GOOGLE_ANDROID_CLIENT_ID",
];

for (const varName of REQUIRED_ALWAYS) {
  if (!env[varName]) {
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

// ---------------------------------------------------------------------------
// Resultado
// ---------------------------------------------------------------------------
for (const w of warnings) console.warn(`WARN: ${w}`);
if (issues.length > 0) {
  console.error("❌ check-capacitor-config FAILED");
  for (const issue of issues) console.error(`  - ${issue}`);
  process.exit(1);
}
console.log("✅ check-capacitor-config PASSED");
process.exit(0);
