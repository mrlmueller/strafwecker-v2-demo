import type { Metadata, Viewport } from "next";
import { Suspense } from "react";
import { NavBar } from "@/app/components/Navbar";
import { DevTokenManager } from "@/app/components/DevTokenManager";
import "./globals.css";
import { ThemeProvider } from "next-themes";

export const metadata: Metadata = {
  title: "Strafwecker",
  description: "Smart alarm system",
  manifest: "/manifest.webmanifest",
  appleWebApp: {
    capable: true,
    title: "Strafwecker",
    statusBarStyle: "black-translucent",
  },
  icons: {
    icon: [
      { url: "/icon.svg", type: "image/svg+xml" },
      { url: "/icon-192.png", sizes: "192x192", type: "image/png" },
      { url: "/icon-512.png", sizes: "512x512", type: "image/png" },
    ],
    apple: [{ url: "/apple-touch-icon.png", sizes: "180x180" }],
  },
};

export const viewport: Viewport = {
  themeColor: "#161616",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-background text-foreground">
        <ThemeProvider attribute="class" defaultTheme="dark">
          <Suspense fallback={null}>
            <DevTokenManager />
          </Suspense>
          <NavBar />
          <main className="p-4 pb-20 md:pb-4 min-h-dvh">{children}</main>
        </ThemeProvider>
      </body>
    </html>
  );
}
