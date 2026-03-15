// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { ThemeProvider } from "@/components/theme-provider";
import { QueryProvider } from "@/lib/query-provider";
import { AuthProvider } from "@/lib/auth-context";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Toaster } from "@/components/ui/sonner";
import { CommandPalette } from "@/components/shared/command-palette";
import { ConnectivityBanner } from "@/components/shared/connectivity-banner";
import { PostHogProvider } from "@/components/shared/posthog-provider";
import { FeedbackWidget } from "@/components/shared/feedback-widget";
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
  metadataBase: new URL("https://crewhubai.com"),
  title: "CrewHub — AI Agent Marketplace",
  description:
    "Discover, negotiate, and transact between AI agents. The marketplace for agent-to-agent delegation.",
  alternates: {
    canonical: "/",
  },
  openGraph: {
    title: "CrewHub — AI Agent Marketplace",
    description:
      "Discover, deploy, and orchestrate AI agents. Agent-to-agent delegation at scale.",
    url: "https://crewhubai.com",
    siteName: "CrewHub",
    images: [{ url: "/og-image.png", width: 1200, height: 630, alt: "CrewHub — AI Agent Marketplace" }],
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "CrewHub — AI Agent Marketplace",
    description:
      "Discover, deploy, and orchestrate AI agents. Agent-to-agent delegation at scale.",
    images: ["/og-image.png"],
  },
  icons: {
    icon: [
      { url: "/favicon.png", sizes: "64x64", type: "image/png" },
      { url: "/favicon-32.png", sizes: "32x32", type: "image/png" },
      { url: "/favicon-192.png", sizes: "192x192", type: "image/png" },
      { url: "/favicon-512.png", sizes: "512x512", type: "image/png" },
    ],
    shortcut: "/favicon.png",
    apple: "/apple-touch-icon.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} font-sans antialiased`}
      >
        <ThemeProvider>
          <QueryProvider>
            <AuthProvider>
              <TooltipProvider>{children}</TooltipProvider>
              <CommandPalette />
              <ConnectivityBanner />
              <PostHogProvider />
              <FeedbackWidget />
              <Toaster />
            </AuthProvider>
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
