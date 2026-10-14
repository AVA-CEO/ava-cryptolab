import type { Metadata } from "next";
import { Providers } from "@/components/providers";
import { AppShell } from "@/components/app-shell";
import "./globals.css";
import "@/styles/journal.css";

export const metadata: Metadata = {
  title: {
    default: "Command Center · AVA CryptoLab",
    template: "%s · AVA CryptoLab",
  },
  description:
    "Analyse. Learn. Trade Smarter. Your cryptocurrency research and education workspace.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <Providers>
          <AppShell>{children}</AppShell>
        </Providers>
      </body>
    </html>
  );
}
