import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TraceVault",
  description: "Replay one AI request without storing raw prompts or raw PII.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
