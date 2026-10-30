import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { AppNav } from "@/components/AppNav";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "PatchPilot — Self-Healing Software Engineer",
  description:
    "Diagnose real bugs, generate minimal patches, and prove fixes through execution.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.variable} font-sans bg-surface text-text-primary min-h-screen antialiased selection:bg-accent/20`}>
        <div className="flex h-screen overflow-hidden ambient-bg">
          <AppNav />
          <main className="flex-1 overflow-y-auto" id="main-content">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
