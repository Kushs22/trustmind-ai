import type { Metadata } from "next";
import { Geist_Mono, Inter } from "next/font/google";
import { HelpChrome } from "@/components/HelpChrome";
import { ThemeProvider } from "@/components/ThemeProvider";
import { WarmupClient } from "@/components/WarmupClient";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
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
      className={`${inter.variable} ${geistMono.variable} scroll-smooth antialiased`}
    >
      <body className="min-h-screen font-sans">
        <ThemeProvider>
          <WarmupClient />
          {children}
          <HelpChrome />
        </ThemeProvider>
      </body>
    </html>
  );
}
