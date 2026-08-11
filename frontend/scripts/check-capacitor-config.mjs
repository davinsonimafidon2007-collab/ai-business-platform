#!/usr/bin/env node
// check-capacitor-config.mjs — Guard de CRIT.002.
//
// Falla (exit 1) si capacitor.config.ts conserva valores placeholder
// 'REPLACE_ME' en la config de GoogleAuth. Sin client IDs reales
// (+ SHA-1 + google-services.json) el Google Login Android queda roto,
// y un APK que se instala con login muerto es peor que un build que falla.
//
// Cross-platform: se ejecuta desde npm scripts (Windows y *nix) y desde
// pre-build-check.sh.

import { readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const CONFIG_PATH = resolve(ROOT, 'capacitor.config.ts');

const PLACEHOLDERS = ['REPLACE_ME', 'YOUR_', 'CHANGE_ME'];

function main() {
  let source;
  try {
    source = readFileSync(CONFIG_PATH, 'utf8');
  } catch (err) {
    console.error(`ERROR: no se pudo leer ${CONFIG_PATH}: ${err.message}`);
    process.exit(1);
  }

  const bad = [];
  for (const placeholder of PLACEHOLDERS) {
    if (source.includes(placeholder)) {
      bad.push(placeholder);
    }
  }

  if (bad.length > 0) {
    console.error('');
    console.error(
      `ERROR (CRIT.002): ${CONFIG_PATH} contiene placeholders sin rellenar: ${bad.join(', ')}`
    );
    console.error('');
    console.error('Google Login Android requiere valores reales:');
    console.error('  1. Google Cloud Console > APIs & Services > Credentials');
    console.error('  2. OAuth client IDs web/Android/iOS (origen de la app).');
    console.error('  3. Añade el SHA-1 de tu keystore al Android client ID.');
    console.error('  4. google-services.json real en android/app/.');
    console.error('  5. Exporta las env vars GOOGLE_WEB_CLIENT_ID /');
    console.error('     GOOGLE_ANDROID_CLIENT_ID / GOOGLE_IOS_CLIENT_ID, o edita');
    console.error('     capacitor.config.ts directamente.');
    console.error('');
    console.error('Si no quieres Google Login todavía, establece el valor en');
    console.error('vacíos (o quita el bloque GoogleAuth) explícitamente.');
    process.exit(1);
  }

  console.log("OK: capacitor.config.ts no contiene placeholders (CRIT.002).");
}

main();
