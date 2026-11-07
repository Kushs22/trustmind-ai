import type { Metadata } from "next";
import { Fraunces, Geist_Mono, Outfit } from "next/font/google";
import { HelpChrome } from "@/components/HelpChrome";
import { ThemeProvider } from "@/components/ThemeProvider";
import { WarmupClient } from "@/components/WarmupClient";
import "./globals.css";

const outfit = Outfit({
  variable: "--font-outfit",
  subsets: ["latin"],
});

const fraunces = Fraunces({
  variable: "--font-fraunces",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "TrustMind AI — a calm place to check in",
  description:
    "Private, non-diagnostic wellbeing check-ins for anyone who needs support. Grounded in trusted UK guidance, with live Bristol help from Nyata AI.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${outfit.variable} ${fraunces.variable} ${geistMono.variable} scroll-smooth antialiased`}
    >
      <body className="min-h-screen font-sans text-stone-800 dark:text-stone-100">
        <ThemeProvider>
          <WarmupClient />
          {children}
          <HelpChrome />
        </ThemeProvider>
      </body>
    </html>
  );
}
