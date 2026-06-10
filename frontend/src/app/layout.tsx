import type { Metadata } from "next";
import { DM_Mono, Instrument_Serif } from "next/font/google";
import "./globals.css";

const dmMono = DM_Mono({
  subsets: ["latin"],
  weight: ["300", "400", "500"],
  variable: "--font-mono",
});

const instrumentSerif = Instrument_Serif({
  subsets: ["latin"],
  weight: "400",
  variable: "--font-serif",
});

export const metadata: Metadata = {
  title: "AI Trust Analyzer",
  description: "Detect hallucination risk and verify claims in AI-generated responses.",
  keywords: ["AI", "hallucination", "fact-check", "trust score", "LLM"],
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`h-full antialiased ${dmMono.variable} ${instrumentSerif.variable}`}>
      <body className="min-h-full flex flex-col bg-surface text-text-primary font-mono">
        {children}
      </body>
    </html>
  );
}