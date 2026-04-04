import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Billing | CortaLoom",
  description: "Manage your CortaLoom subscription, usage, and overage budget.",
};

export default function BillingLayout({ children }: { children: React.ReactNode }) {
  return children;
}
