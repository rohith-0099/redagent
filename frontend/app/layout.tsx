import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";

// Self-hosted IBM Plex Mono — no build-time network font fetch (Cloud Run safe).
const mono = localFont({
  src: [
    { path: "./fonts/ibm-plex-mono-latin-400-normal.woff2", weight: "400", style: "normal" },
    { path: "./fonts/ibm-plex-mono-latin-500-normal.woff2", weight: "500", style: "normal" },
    { path: "./fonts/ibm-plex-mono-latin-600-normal.woff2", weight: "600", style: "normal" },
    { path: "./fonts/ibm-plex-mono-latin-700-normal.woff2", weight: "700", style: "normal" },
  ],
  variable: "--font-plex-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "RedAgent — Red-Team Console",
  description:
    "Multi-agent AI safety red-teaming console. Attacks stream live; a human approves the fix.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={mono.variable}>
      <body>
        <div id="app-root">{children}</div>
      </body>
    </html>
  );
}
