"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, ScrollText, Wifi } from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { name: "Home", href: "/", icon: Home },
  { name: "Logs", href: "/logs", icon: ScrollText },
  { name: "Network", href: "/network", icon: Wifi },
];

export function NavBar() {
  const pathname = usePathname();

  return (
    <>
      {/* Desktop: sticky top header */}
      <header className="hidden md:flex sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-14 items-center justify-between">
          <Link href="/" className="flex items-center space-x-2">
            <span className="font-bold">Strafwecker</span>
          </Link>
          <nav className="flex items-center space-x-6 text-sm font-medium">
            {navItems.map((item) => {
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={cn(
                    "transition-colors hover:text-foreground/80",
                    isActive ? "text-foreground" : "text-foreground/60"
                  )}
                >
                  {item.name}
                </Link>
              );
            })}
          </nav>
        </div>
      </header>

      {/* Mobile: fixed bottom tab bar — height includes safe-area-inset-bottom for home indicator */}
      <nav
        className="md:hidden fixed bottom-0 left-0 right-0 z-50 border-t bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60"
        style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}
      >
        <div className="grid h-16 grid-cols-3">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  "relative flex flex-col items-center justify-center gap-1 transition-colors",
                  isActive ? "text-foreground" : "text-foreground/50"
                )}
              >
                <item.icon className="h-5 w-5" />
                <span className="text-xs font-medium">{item.name}</span>
                {isActive && (
                  <span className="absolute top-0 left-1/2 -translate-x-1/2 h-0.5 w-10 rounded-b-full bg-primary" />
                )}
              </Link>
            );
          })}
        </div>
      </nav>
    </>
  );
}
