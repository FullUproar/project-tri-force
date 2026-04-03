import { auth } from "@clerk/nextjs/server";
import { LandingPage } from "@/components/landing-page";
import { DashboardWrapper } from "@/components/dashboard-wrapper";

export default async function RootPage() {
  const { userId } = await auth();

  if (!userId) {
    return <LandingPage />;
  }

  return <DashboardWrapper />;
}
