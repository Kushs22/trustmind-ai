import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { HelpChrome } from "@/components/HelpChrome";
import { ThemeProvider } from "@/components/ThemeProvider";
import { WarmupClient } from "@/components/WarmupClient";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
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
      className={`${geistSans.variable} ${geistMono.variable} scroll-smooth antialiased`}
    >
      <body className="min-h-screen font-sans text-slate-800 dark:text-slate-100">
        <ThemeProvider>
          <WarmupClient />
          {children}
          <HelpChrome />
        </ThemeProvider>
      </body>
    </html>
  );
}
