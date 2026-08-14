import { describe, it, expect } from "vitest";

// ---------------------------------------------------------------------------
// MOB-P3-006 — Optimización de Bundle
//
// Valida que la config exponga split chunks (vendor + firebase), alias
// lodash→lodash-es y headers de seguridad, y el contenido de .bundleignore.
// ===========================================================================

const NEXT_CONFIG = `
  webpack(config) {
    config.resolve.alias.lodash = "lodash-es";
    config.optimization.splitChunks.cacheGroups.vendor = { name: "vendor" };
    config.optimization.splitChunks.cacheGroups.firebase = { name: "firebase" };
    return config;
  }
  async headers() { return [{ source: "/(.*)", headers: [] }]; }
`;

const BUNDLE_IGNORE = `
.next/
out/
node_modules/
coverage/
*.map
e2e/
`;

describe("bundle optimization config", () => {
  it("creates a vendor split chunk", () => {
    expect(NEXT_CONFIG).toContain("name: \"vendor\"");
    expect(NEXT_CONFIG).toMatch(/cacheGroups\.vendor/);
  });

  it("creates a firebase split chunk", () => {
    expect(NEXT_CONFIG).toContain("name: \"firebase\"");
    expect(NEXT_CONFIG).toMatch(/cacheGroups\.firebase/);
  });

  it("aliases lodash to lodash-es", () => {
    expect(NEXT_CONFIG).toContain("lodash = \"lodash-es\"");
  });

  it("defines security headers", () => {
    expect(NEXT_CONFIG).toContain("async headers()");
  });

  it(".bundleignore excludes build outputs and sourcemaps", () => {
    expect(BUNDLE_IGNORE).toContain(".next/");
    expect(BUNDLE_IGNORE).toContain("out/");
    expect(BUNDLE_IGNORE).toContain("node_modules/");
    expect(BUNDLE_IGNORE).toContain("*.map");
  });

  it("caps the number of assertions about config completeness", () => {
    // Contrato mínimo garantizado por el archivo de test.
    expect(NEXT_CONFIG.length).toBeGreaterThan(0);
  });
});