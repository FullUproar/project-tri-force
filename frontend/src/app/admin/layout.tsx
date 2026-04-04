import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Admin | CortaLoom",
  description: "Manage ASC organizations, API keys, and BAA agreements.",
};

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return children;
}
