"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { UserButton } from "@clerk/nextjs";
import { LayoutDashboard, BarChart3, Settings, CreditCard, BookOpen, Users, Menu, X, FolderOpen } from "lucide-react";
import { cn } from "@/lib/utils";
import { useState, useEffect } from "react";

const NAV_ITEMS = [
  { href: "/", label: "Home", icon: LayoutDashboard },
  { href: "/cases", label: "Cases", icon: FolderOpen },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/billing", label: "Billing", icon: CreditCard },
];

const ADMIN_ITEMS = [
  { href: "/rep", label: "Sales", icon: Users },
  { href: "/admin", label: "Admin", icon: Settings },
];

export function NavBar() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  // Close mobile menu on navigation
  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  const { data: orgInfo } = useQuery<{ is_admin: boolean }>({
    queryKey: ["me"],
    queryFn: async () => {
      const res = await fetch("/api/proxy/api/v1/me");
      if (!res.ok) return { is_admin: false };
      return res.json();
    },
    staleTime: 60000,
  });

  const allItems = orgInfo?.is_admin ? [...NAV_ITEMS, ...ADMIN_ITEMS] : NAV_ITEMS;

  return (
    <header className="border-b border-[var(--border)] px-6 py-3">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-6">
          <Link href="/" className="flex items-center gap-2">
            <Image src="/logo-globe.webp" alt="CortaLoom logo" width={32} height={32} />
            <span className="text-lg font-bold">CortaLoom</span>
          </Link>
          <nav className="hidden md:flex items-center gap-1">
            {allItems.map(({ href, label, icon: Icon }) => (
              <Link
                key={href}
                href={href}
                className={cn(
                  "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm transition-colors",
                  (pathname === href || (href !== "/" && pathname.startsWith(href)))
                    ? "bg-[var(--primary)] text-[var(--primary-foreground)]"
                    : "text-[var(--muted-foreground)] hover:bg-[var(--muted)] hover:text-[var(--foreground)]"
                )}
              >
                <Icon className="w-3.5 h-3.5" />
                {label}
              </Link>
            ))}
          </nav>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setMobileOpen((prev) => !prev)}
            className="md:hidden p-1.5 rounded hover:bg-[var(--muted)] transition-colors"
            aria-label="Toggle menu"
          >
            {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
          <UserButton />
        </div>
      </div>

      {/* Mobile menu */}
      {mobileOpen && (
        <nav className="md:hidden mt-3 pb-2 border-t border-[var(--border)] pt-3 space-y-1">
          {allItems.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors",
                (pathname === href || (href !== "/" && pathname.startsWith(href)))
                  ? "bg-[var(--primary)] text-[var(--primary-foreground)]"
                  : "text-[var(--muted-foreground)] hover:bg-[var(--muted)] hover:text-[var(--foreground)]"
              )}
            >
              <Icon className="w-4 h-4" />
              {label}
            </Link>
          ))}
        </nav>
      )}
    </header>
  );
}
