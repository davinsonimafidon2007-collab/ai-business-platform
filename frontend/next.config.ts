import type { NextConfig } from "next";
import path from "path";

// MOB-P3-006 — Optimización de bundle:
//  - Separar vendor externo y firebase en chunks propios (cache-rotación).
//  - Alias lodash → lodash-es (tree-shaking más agresivo).
//  - Headers de seguridad en respuestas.
// La config de webpack es un función que puede devolver undefined para
// cohexistir con otras configs (bundle-analyzer).
const nextConfig: NextConfig = {
  images: {
    unoptimized: true,
  },
  trailingSlash: true,
  skipTrailingSlashRedirect: true,
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

export default nextConfig;
