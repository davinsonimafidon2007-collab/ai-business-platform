import type { NextConfig } from "next";
import path from "path";

// MOBILE-HARDENING #8: VERSION en la raíz del repo es la única fuente de
// verdad de versión (Android versionName/versionCode y backend /mobile/version
// derivan de él). Si no viene NEXT_PUBLIC_APP_VERSION del entorno, se lee del
// archivo; si tampoco existe, fallback seguro 1.0.0.
const fs = require("fs") as typeof import("fs");
function resolveAppVersion(): string {
  const fromEnv = process.env.NEXT_PUBLIC_APP_VERSION;
  if (fromEnv && /^\d+\.\d+\.\d+$/.test(fromEnv)) return fromEnv;
  try {
    const raw = fs
      .readFileSync(path.join(__dirname, "..", "VERSION"), "utf-8")
      .trim();
    if (/^\d+\.\d+\.\d+$/.test(raw)) return raw;
  } catch {
    // archivo ausente → fallback
  }
  return "1.0.0";
}

// MOB-P3-006 / PWA (Bloque 1.3): service worker + manifest instalable.
// next-pwa v5 es CommonJS, por eso se usa require() dentro de un .ts.
const withPWA = require("next-pwa")({
  dest: "public",
  register: true,
  skipWaiting: true,
  disable: process.env.NODE_ENV === "development",
});

// BUILD_TARGET=capacitor -> export estático (usado por Android/Capacitor).
// BUILD_TARGET=docker   -> build de servidor con output standalone (imagen
//                          mínima sin node_modules completo en runtime).
// Sin BUILD_TARGET (o cualquier otro valor) -> build de servidor normal,
// necesario para que `next start` funcione en Docker/producción web.
const buildTarget = process.env.BUILD_TARGET;
const isCapacitorBuild = buildTarget === "capacitor";
const isDockerBuild = buildTarget === "docker";

// MOB-P3-006 — Optimización de bundle:
//  - Separar vendor externo y firebase en chunks propios (cache-rotación).
//  - Alias lodash → lodash-es (tree-shaking más agresivo).
//  - Headers de seguridad en respuestas.
// La config de webpack es un función que puede devolver undefined para
// cohexistir con otras configs (bundle-analyzer).
const nextConfig: NextConfig = {
  // MOBILE-HARDENING #8: inyecta la versión de build desde VERSION.
  env: {
    NEXT_PUBLIC_APP_VERSION: resolveAppVersion(),
  },
  ...(isCapacitorBuild
    ? {
        output: "export" as const,
        trailingSlash: true,
        skipTrailingSlashRedirect: true,
      }
    : {}),
  ...(isDockerBuild ? { output: "standalone" as const } : {}),
  images: {
    unoptimized: true,
  },
  outputFileTracingRoot: path.join(__dirname, "../"),
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
        ],
      },
    ];
  },
  webpack(config) {
    // Alias lodash → lodash-es para permitir tree-shaking.
    if (config.resolve && config.resolve.alias) {
      config.resolve.alias.lodash = "lodash-es";
    }
    // Split chunks: vendor (react/next) y firebase en bloques propios.
    if (config.optimization && config.optimization.splitChunks) {
      const split = config.optimization.splitChunks;
      if (split.cacheGroups) {
        split.cacheGroups.vendor = {
          name: "vendor",
          test: /[\\/]node_modules[\\/](react|react-dom|next)[\\/]/,
          chunks: "all",
          priority: 10,
          enforce: true,
        };
        split.cacheGroups.firebase = {
          name: "firebase",
          test: /[\\/]node_modules[\\/].*(?:firebase)[\\/]/,
          chunks: "all",
          priority: 10,
          enforce: true,
        };
      }
    }
    return config;
  },
};

export default withPWA(nextConfig);
