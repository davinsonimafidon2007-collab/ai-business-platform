// MED.008: client IDs de Google centralizados en un solo lugar para que
// google-auth.ts (y el resto del frontend) no los duplique por capas.
//
// Tanto capacitor.config.ts (`cap sync`, evaluado en Node sin Next.js) como
// google-auth.ts (bundle del navegador) importan AQUÍ, de modo que siempre
// usan los mismos valores.
//
// Se aceptan las dos nomenclaturas de env: con prefijo NEXT_PUBLIC_ (para el
// bundle de Next) y sin prefijo (GOOGLE_*, para el proceso de `cap sync`).
// Web: client_type 3 de google-services.json. Android: client_type 1.
export const GOOGLE_WEB_CLIENT_ID =
  process.env.NEXT_PUBLIC_GOOGLE_WEB_CLIENT_ID ||
  process.env.GOOGLE_WEB_CLIENT_ID ||
  "983773208764-oevega4uglktmrisjrh41teq5mjb270n.apps.googleusercontent.com";

export const GOOGLE_ANDROID_CLIENT_ID =
  process.env.NEXT_PUBLIC_GOOGLE_ANDROID_CLIENT_ID ||
  process.env.GOOGLE_ANDROID_CLIENT_ID ||
  "983773208764-7i0hfifq4ni324qnugvj0a79bu09fh4t.apps.googleusercontent.com";

export const GOOGLE_IOS_CLIENT_ID =
  process.env.NEXT_PUBLIC_GOOGLE_IOS_CLIENT_ID ||
  process.env.GOOGLE_IOS_CLIENT_ID ||
  GOOGLE_WEB_CLIENT_ID;
