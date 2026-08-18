import CryptoJS from "crypto-js";

const SECRET_KEY = process.env.NEXT_PUBLIC_STORAGE_SECRET || "default-secret-abp";

export function encryptData(data: string): string {
  return CryptoJS.AES.encrypt(data, SECRET_KEY).toString();
}

export function decryptData(encrypted: string): string {
  try {
    const bytes = CryptoJS.AES.decrypt(encrypted, SECRET_KEY);
    return bytes.toString(CryptoJS.enc.Utf8);
  } catch {
    return "";
  }
}

export function setSecureItem(key: string, value: string): void {
  if (typeof window !== "undefined") {
    localStorage.setItem(key, encryptData(value));
  }
}

export function getSecureItem(key: string): string | null {
  if (typeof window === "undefined") return null;
  const encrypted = localStorage.getItem(key);
  if (!encrypted) return null;
  try {
    return decryptData(encrypted) || null;
  } catch {
    return null;
  }
}
