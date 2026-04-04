import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Sales Dashboard | CortaLoom",
  description: "Cross-tenant sales metrics, pipeline tracking, and MRR overview.",
};

export default function RepLayout({ children }: { children: React.ReactNode }) {
  return children;
}
