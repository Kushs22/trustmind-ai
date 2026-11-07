import type { Metadata, Viewport } from "next";
import { Instrument_Serif, Inter } from "next/font/google";
import { HelpChrome } from "@/components/HelpChrome";
import { ThemeProvider } from "@/components/ThemeProvider";
import { WarmupClient } from "@/components/WarmupClient";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const instrument = Instrument_Serif({
  variable: "--font-instrument",
  subsets: ["latin"],
  weight: "400",
  style: ["normal", "italic"],
});

export const metadata: Metadata = {
  title: "TrustMind AI — a calm place to check in",
  description:
    "Private, non-diagnostic wellbeing check-ins for anyone who needs support. Grounded in trusted UK guidance, with live Bristol help from Nyata AI.",
  openGraph: {
    title: "TrustMind AI — a calm place to check in",
    description:
      "Private, non-diagnostic wellbeing check-ins for anyone who needs support. No account required.",
    images: [{ url: "/og-image.png", width: 1200, height: 630 }],
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "TrustMind AI — a calm place to check in",
    description:
      "Private, non-diagnostic wellbeing check-ins for anyone who needs support. No account required.",
    images: ["/og-image.png"],
  },
  icons: {
    icon: "/favicon.svg",
    apple: "/apple-icon.svg",
  },
};

export const viewport: Viewport = {
  themeColor: "#2A5C45",
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
      className={`${inter.variable} ${instrument.variable} scroll-smooth antialiased`}
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
