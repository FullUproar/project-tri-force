"use client";

import { useQuery } from "@tanstack/react-query";
import { Building2, DollarSign, FileCheck, Shield, ShieldCheck, Users, TrendingUp } from "lucide-react";
import { NavBar } from "@/components/nav-bar";
import { cn } from "@/lib/utils";

const API_BASE = "/api/proxy/api/v1";

interface OrgSummary {
  id: string;
  name: string;
  is_active: boolean;
  baa_signed_at: string | null;
  job_count: number;
  extraction_count: number;
}

export default function RepDashboard() {
  const { data: orgs } = useQuery<OrgSummary[]>({
    queryKey: ["admin-orgs"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/admin/organizations`);
      if (!res.ok) return [];
      return res.json();
    },
    refetchInterval: 30000,
  });

  const totalOrgs = orgs?.length || 0;
  const activeOrgs = orgs?.filter((o) => o.baa_signed_at) || [];
  const totalExtractions = orgs?.reduce((sum, o) => sum + o.extraction_count, 0) || 0;
  const totalJobs = orgs?.reduce((sum, o) => sum + o.job_count, 0) || 0;

  // Estimated MRR (rough — assumes all active orgs on Professional plan)
  const estimatedMRR = activeOrgs.length * 299;
  const timeSavedHours = Math.round(totalExtractions * 44 / 60);

  return (
    <div className="min-h-screen bg-[var(--background)]">
      <NavBar />

      <main className="max-w-6xl mx-auto p-6 space-y-8">
        <div>
          <h1 className="text-2xl font-bold">Sales Dashboard</h1>
          <p className="text-sm text-[var(--muted-foreground)]">
            Cross-tenant overview — all CortaLoom ASC customers
          </p>
        </div>

        {/* Revenue Metrics */}
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
          <div className="p-5 border border-[var(--border)] rounded-xl">
            <div className="flex items-center gap-2 mb-1">
              <Building2 className="w-4 h-4 text-blue-600" />
              <span className="text-xs text-[var(--muted-foreground)]">Organizations</span>
            </div>
            <p className="text-2xl font-bold">{totalOrgs}</p>
          </div>
          <div className="p-5 border border-[var(--border)] rounded-xl">
            <div className="flex items-center gap-2 mb-1">
              <ShieldCheck className="w-4 h-4 text-green-600" />
              <span className="text-xs text-[var(--muted-foreground)]">BAA Signed</span>
            </div>
            <p className="text-2xl font-bold">{activeOrgs.length}</p>
          </div>
          <div className="p-5 border border-[var(--border)] rounded-xl">
            <div className="flex items-center gap-2 mb-1">
              <DollarSign className="w-4 h-4 text-green-600" />
              <span className="text-xs text-[var(--muted-foreground)]">Est. MRR</span>
            </div>
            <p className="text-2xl font-bold">${estimatedMRR.toLocaleString()}</p>
          </div>
          <div className="p-5 border border-[var(--border)] rounded-xl">
            <div className="flex items-center gap-2 mb-1">
              <FileCheck className="w-4 h-4 text-purple-600" />
              <span className="text-xs text-[var(--muted-foreground)]">Total Extractions</span>
            </div>
            <p className="text-2xl font-bold">{totalExtractions}</p>
          </div>
          <div className="p-5 border border-[var(--border)] rounded-xl">
            <div className="flex items-center gap-2 mb-1">
              <TrendingUp className="w-4 h-4 text-orange-600" />
              <span className="text-xs text-[var(--muted-foreground)]">Hours Saved (all)</span>
            </div>
            <p className="text-2xl font-bold">{timeSavedHours}</p>
          </div>
        </div>

        {/* Organization Table */}
        <div className="border border-[var(--border)] rounded-xl overflow-hidden">
          <div className="px-6 py-4 bg-[var(--muted)]">
            <h2 className="font-bold">All Organizations</h2>
          </div>
          <div className="divide-y divide-[var(--border)]">
            {orgs?.map((org) => (
              <div key={org.id} className="px-6 py-4 flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div
                    className={cn(
                      "w-10 h-10 rounded-lg flex items-center justify-center text-sm font-bold",
                      org.baa_signed_at
                        ? "bg-green-100 text-green-700"
                        : "bg-yellow-100 text-yellow-700"
                    )}
                  >
                    {org.name.charAt(0)}
                  </div>
                  <div>
                    <p className="font-medium">{org.name}</p>
                    <div className="flex items-center gap-3 text-xs text-[var(--muted-foreground)]">
                      <span>{org.job_count} jobs</span>
                      <span>{org.extraction_count} extractions</span>
                      <span className="flex items-center gap-1">
                        {org.baa_signed_at ? (
                          <>
                            <ShieldCheck className="w-3 h-3 text-green-500" />
                            BAA signed
                          </>
                        ) : (
                          <>
                            <Shield className="w-3 h-3 text-yellow-500" />
                            BAA pending
                          </>
                        )}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {org.extraction_count > 0 && (
                    <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs font-medium">
                      Active
                    </span>
                  )}
                  {!org.baa_signed_at && (
                    <span className="px-2 py-0.5 bg-yellow-100 text-yellow-700 rounded text-xs font-medium">
                      Onboarding
                    </span>
                  )}
                </div>
              </div>
            ))}
            {(!orgs || orgs.length === 0) && (
              <div className="px-6 py-8 text-center text-[var(--muted-foreground)] text-sm">
                No organizations yet. Create one from the Admin page.
              </div>
            )}
          </div>
        </div>

        {/* Pipeline Summary */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="p-6 border border-dashed border-yellow-300 bg-yellow-50/50 rounded-xl">
            <h3 className="font-bold text-yellow-800">Onboarding</h3>
            <p className="text-3xl font-bold text-yellow-700 mt-2">
              {orgs?.filter((o) => !o.baa_signed_at).length || 0}
            </p>
            <p className="text-xs text-yellow-600 mt-1">Awaiting BAA signature</p>
          </div>
          <div className="p-6 border border-dashed border-blue-300 bg-blue-50/50 rounded-xl">
            <h3 className="font-bold text-blue-800">Active Pilots</h3>
            <p className="text-3xl font-bold text-blue-700 mt-2">
              {orgs?.filter((o) => o.baa_signed_at && o.extraction_count > 0).length || 0}
            </p>
            <p className="text-xs text-blue-600 mt-1">BAA signed + processing cases</p>
          </div>
          <div className="p-6 border border-dashed border-green-300 bg-green-50/50 rounded-xl">
            <h3 className="font-bold text-green-800">Converted</h3>
            <p className="text-3xl font-bold text-green-700 mt-2">
              {orgs?.filter((o) => o.extraction_count >= 10).length || 0}
            </p>
            <p className="text-xs text-green-600 mt-1">10+ extractions (power users)</p>
          </div>
        </div>
      </main>
    </div>
  );
}
