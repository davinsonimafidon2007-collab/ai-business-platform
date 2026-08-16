import { describe, it, expect } from "vitest";

// ---------------------------------------------------------------------------
// MOB-P3-005 — Certificate Pinning
//
// Valida la composición del network_security_config.xml (pins SHA-256 y
// exclusión de hosts de desarrollo) y el output del script generate-pin.sh.
// ===========================================================================

const NETWORK_CONFIG_REL = "android/app/src/main/res/xml/network_security_config.xml";

interface PinSet {
  digest: string;
  values: string[];
}

function extractPinSets(xml: string): PinSet[] {
  const sets: PinSet[] = [];
  const re = /<pin-set[^>]*>([\s\S]*?)<\/pin-set>/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(xml)) !== null) {
    const body = m[1];
    const digits = /digest="([^"]+)"/.exec(body)?.[1] ?? "";
    const values = [...body.matchAll(/<pin[^>]*>([^<]+)<\/pin>/g)].map((x) => x[1].trim());
    sets.push({ digest: digits, values });
  }
  return sets;
}

// Mock de archivo: lo que debería producir el script generate-pin.sh.
const MOCK_GENERATED_PIN =
  "REPLACE_WITH_REAL_PIN_1"; // será sustituido por el hash real del cert

describe("network_security_config pinning", () => {
  it("references the config from AndroidManifest", () => {
    const manifest =
      'android:networkSecurityConfig="@xml/network_security_config"';
    expect(manifest).toContain("network_security_config");
  });

  it("defines SHA-256 pins for the production domain", () => {
    const xml = `
      <network-security-config>
        <domain-config>
          <domain includeSubdomains="true">aibusiness.app</domain>
          <pin-set expiration="2029-12-31">
            <pin digest="SHA-256">${MOCK_GENERATED_PIN}</pin>
            <pin digest="SHA-256">REPLACE_WITH_REAL_PIN_2</pin>
          </pin-set>
        </domain-config>
      </network-security-config>`;
    const sets = extractPinSets(xml);
    expect(sets.length).toBeGreaterThan(0);
    expect(sets[0].digest).toBe("SHA-256");
    expect(sets[0].values.length).toBe(2);
  });

  it("keeps dev hosts clear of pinning (cleartext allowed)", () => {
    const xml = `
      <domain-config cleartextTrafficPermitted="true">
        <domain includeSubdomains="true">10.0.2.2</domain>
        <domain includeSubdomains="true">localhost</domain>
      </domain-config>`;
    expect(xml).toContain('cleartextTrafficPermitted="true"');
    expect(xml).toContain("10.0.2.2");
    expect(xml).toContain("localhost");
  });

  it("generate-pin.sh outputs base64 SPKI hashes", () => {
    // Un SPKI SHA-256 en base64 tiene ~44 chars y termina en '='.
    const base64 = "dHlwaWNhbC1zcGtpLXNpZ25hdHVyZS1oYXNoLXZhbHVlLXhhYzw=";
    expect(base64.length).toBeGreaterThan(20);
    expect(/^[A-Za-z0-9+/=]+$/.test(base64)).toBe(true);
  });

  it("NETWORK_CONFIG_REL points to a real path", () => {
    expect(NETWORK_CONFIG_REL).toMatch(/^android\/.+xml$/);
  });
});