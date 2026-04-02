"use client";

import { useAuth } from "@clerk/nextjs";
import { LandingPage } from "@/components/landing-page";
import { Dashboard } from "@/components/dashboard";

export default function RootPage() {
  const { isSignedIn, isLoaded } = useAuth();

  if (!isLoaded) return null;

  if (!isSignedIn) {
    return <LandingPage />;
  }

  return <Dashboard />;
}
