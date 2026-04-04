import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Analytics | CortaLoom",
  description: "Track prior authorization outcomes, approval rates, and time saved across your ASC.",
};

export default function AnalyticsLayout({ children }: { children: React.ReactNode }) {
  return children;
}
