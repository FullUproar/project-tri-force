import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Setup Guide | CortaLoom",
  description: "Get your ASC set up on CortaLoom — BAA, billing, and first case.",
};

export default function OnboardingLayout({ children }: { children: React.ReactNode }) {
  return children;
}
