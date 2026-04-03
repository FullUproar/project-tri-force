"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { UserButton } from "@clerk/nextjs";
import { LayoutDashboard, BarChart3, Settings, CreditCard, BookOpen, Users } from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/billing", label: "Billing", icon: CreditCard },
  { href: "/onboarding", label: "Setup Guide", icon: BookOpen },
];

const ADMIN_ITEMS = [
  { href: "/rep", label: "Sales", icon: Users },
  { href: "/admin", label: "Admin", icon: Settings },
];

export function NavBar() {
  const pathname = usePathname();

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
            <img src="/logo-globe.webp" alt="CortaLoom" className="w-8 h-8" />
            <span className="text-lg font-bold">CortaLoom</span>
          </Link>
          <nav className="hidden md:flex items-center gap-1">
            {allItems.map(({ href, label, icon: Icon }) => (
              <Link
                key={href}
                href={href}
                className={cn(
                  "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm transition-colors",
                  pathname === href
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
        <UserButton />
      </div>
    </header>
  );
}
