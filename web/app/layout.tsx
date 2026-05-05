import type { Metadata } from "next";
import { IBM_Plex_Sans, IBM_Plex_Serif } from "next/font/google";
import "./globals.css";

// IBM Plex — designed for clinical and technical interfaces.
// Used by IBM Watson Health, the WHO publication system, and many medical journals.
// Reads like documentation, not a startup landing page.

const plexSans = IBM_Plex_Sans({
  subsets: ["latin"],
  variable: "--font-plex-sans",
  display: "swap",
  weight: ["400", "500", "600"],
});

const plexSerif = IBM_Plex_Serif({
  subsets: ["latin"],
  variable: "--font-plex-serif",
  display: "swap",
  weight: ["400", "500", "600"],
  style: ["normal", "italic"],
});

export const metadata: Metadata = {
  metadataBase: new URL("https://malaika.health"),
  title: {
    default: "Malaika — open-source WHO IMCI assistant, on any phone, fully offline",
    template: "%s · Malaika",
  },
  description:
    "Pneumonia kills a child every thirty-nine seconds. Malaika puts the WHO's child-survival protocol into any caregiver's hand — in her language, through her phone, powered by Gemma 4. Offline, free, open source.",
  keywords: [
    "WHO IMCI",
    "child survival",
    "Gemma 4",
    "pneumonia",
    "edge AI",
    "offline AI",
    "open source health",
    "rural health",
    "global health",
  ],
  authors: [{ name: "Vimal Kumar" }, { name: "Mark D. Hei Long" }],
  openGraph: {
    title: "Malaika — every thirty-nine seconds",
    description:
      "Open-source WHO IMCI assistant on a $60 Android phone, fully offline. Powered by Gemma 4.",
    url: "https://malaika.health",
    siteName: "Malaika",
    locale: "en_US",
    type: "website",
  },
  robots: { index: true, follow: true },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${plexSans.variable} ${plexSerif.variable}`}>
      <body>{children}</body>
    </html>
  );
}
