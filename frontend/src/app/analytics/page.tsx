"use client";

import { useQuery } from "@tanstack/react-query";
import { TrendingUp, Clock, FileCheck, Target } from "lucide-react";
import { cn } from "@/lib/utils";

const API_BASE = "/api/proxy/api/v1";

interface OutcomeStats {
  total_with_outcome: number;
  approved: number;
  denied: number;
  pending: number;
  appealed: number;
  approval_rate: number | null;
}

interface UsageStats {
  total_jobs: number;
  total_extractions: number;
  avg_confidence: number;
  estimated_time_saved_minutes: number;
}

function StatCard({
  label,
  value,
  icon: Icon,
  color,
}: {
  label: string;
  value: string | number;
  icon: React.ElementType;
  color: string;
}) {
  return (
    <div className="p-5 border border-[var(--border)] rounded-xl">
      <div className="flex items-center gap-3">
        <div className={cn("p-2 rounded-lg", color)}>
          <Icon className="w-5 h-5" />
        </div>
        <div>
          <p className="text-2xl font-bold">{value}</p>
          <p className="text-xs text-[var(--muted-foreground)]">{label}</p>
        </div>
      </div>
    </div>
  );
}

function OutcomeBar({ label, count, total, color }: { label: string; count: number; total: number; color: string }) {
  const pct = total > 0 ? (count / total) * 100 : 0;
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="font-medium capitalize">{label}</span>
        <span className="text-[var(--muted-foreground)]">{count} ({Math.round(pct)}%)</span>
      </div>
      <div className="w-full bg-[var(--muted)] rounded-full h-3">
        <div className={cn("h-3 rounded-full transition-all", color)} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export default function AnalyticsPage() {
  const { data: outcomes } = useQuery<OutcomeStats>({
    queryKey: ["analytics-outcomes"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/analytics/outcomes`);
      return res.json();
    },
    refetchInterval: 30000,
  });

  const { data: usage } = useQuery<UsageStats>({
    queryKey: ["analytics-usage"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/analytics/usage`);
      return res.json();
    },
    refetchInterval: 30000,
  });

  const timeSavedHours = usage ? Math.round(usage.estimated_time_saved_minutes / 60) : 0;

  return (
    <div className="min-h-screen bg-[var(--background)]">
      <header className="border-b border-[var(--border)] px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center gap-3">
          <img src="/logo-globe.webp" alt="CortaLoom" className="w-9 h-9" />
          <div>
            <h1 className="text-xl font-bold">Analytics</h1>
            <p className="text-xs text-[var(--muted-foreground)]">
              Prior Authorization Performance
            </p>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto p-6 space-y-8">
        {/* Stat Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            label="Total Cases"
            value={usage?.total_extractions || 0}
            icon={FileCheck}
            color="bg-blue-100 text-blue-700"
          />
          <StatCard
            label="Approval Rate"
            value={outcomes?.approval_rate ? `${outcomes.approval_rate}%` : "—"}
            icon={Target}
            color="bg-green-100 text-green-700"
          />
          <StatCard
            label="Hours Saved"
            value={timeSavedHours}
            icon={Clock}
            color="bg-purple-100 text-purple-700"
          />
          <StatCard
            label="Avg Confidence"
            value={usage ? `${Math.round(usage.avg_confidence * 100)}%` : "—"}
            icon={TrendingUp}
            color="bg-orange-100 text-orange-700"
          />
        </div>

        {/* Outcome Breakdown */}
        {outcomes && outcomes.total_with_outcome > 0 && (
          <div className="p-6 border border-[var(--border)] rounded-xl space-y-4">
            <h2 className="font-bold">Outcome Breakdown</h2>
            <OutcomeBar label="Approved" count={outcomes.approved} total={outcomes.total_with_outcome} color="bg-green-500" />
            <OutcomeBar label="Denied" count={outcomes.denied} total={outcomes.total_with_outcome} color="bg-red-500" />
            <OutcomeBar label="Pending" count={outcomes.pending} total={outcomes.total_with_outcome} color="bg-yellow-500" />
            <OutcomeBar label="Appealed" count={outcomes.appealed} total={outcomes.total_with_outcome} color="bg-blue-500" />
          </div>
        )}

        {/* Empty State */}
        {(!outcomes || outcomes.total_with_outcome === 0) && (
          <div className="p-8 text-center border border-dashed border-[var(--border)] rounded-xl">
            <p className="text-sm text-[var(--muted-foreground)]">
              No outcome data yet. Mark cases as approved/denied in the dashboard to see analytics here.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
