import type { Metadata, Viewport } from "next";
import "./globals.css";
import { Providers } from "@/app/providers";
import { OfflineBanner } from "@/app/hooks/use-offline";

export const metadata: Metadata = {
  title: "AI Business Platform",
  description: "Vehicle import analysis and market intelligence platform",
};

// Status bar / browser chrome color (MOBILE.THEME.1) — violet premium.
export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#7c3aed" },
    { media: "(prefers-color-scheme: dark)", color: "#0b0614" },
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es" suppressHydrationWarning>
      <body className="antialiased">
        <Providers>
          <OfflineBanner />
          {children}
        </Providers>
      </body>
    </html>
  );
}
