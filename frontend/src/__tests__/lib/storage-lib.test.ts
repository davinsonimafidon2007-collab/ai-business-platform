import { encryptData, decryptData, setSecureItem, getSecureItem } from "@/lib/storage";

describe("lib/storage", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("encrypts and decrypts string data", () => {
    const original = "my-secret-token";
    const encrypted = encryptData(original);
    expect(encrypted).not.toBe(original);
    const decrypted = decryptData(encrypted);
    expect(decrypted).toBe(original);
  });

  it("sets and gets secure items in localStorage", () => {
    setSecureItem("test_key", "secret_val");
    const retrieved = getSecureItem("test_key");
    expect(retrieved).toBe("secret_val");
  });

  it("returns null for non-existing or invalid item", () => {
    expect(getSecureItem("non_existing_key_abc")).toBeNull();
  });
});
