"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Upload, FileCheck, Clock, Target, TrendingUp, CreditCard, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";

const API_BASE = "/api/proxy/api/v1";

interface UsageStats {
  total_jobs: number;
  total_extractions: number;
  avg_confidence: number;
  estimated_time_saved_minutes: number;
}

interface OutcomeStats {
  total_with_outcome: number;
  approved: number;
  denied: number;
  pending: number;
  appealed: number;
  approval_rate: number | null;
}

interface BillingStatus {
  subscription_tier: string | null;
  usage: {
    extractions_used: number;
    extractions_included: number;
    overage_count: number;
  };
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
        <div className={cn("p-2.5 rounded-lg", color)}>
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

export function ASCHome() {
  const { data: usage } = useQuery<UsageStats>({
    queryKey: ["analytics-usage"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/analytics/usage`);
      return res.json();
    },
  });

  const { data: outcomes } = useQuery<OutcomeStats>({
    queryKey: ["analytics-outcomes"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/analytics/outcomes`);
      return res.json();
    },
  });

  const { data: billing } = useQuery<BillingStatus>({
    queryKey: ["billing-status"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/billing/status`);
      return res.json();
    },
  });

  const timeSavedHours = usage ? Math.round(usage.estimated_time_saved_minutes / 60) : 0;
  const usagePct = billing?.usage
    ? Math.round((billing.usage.extractions_used / Math.max(1, billing.usage.extractions_included)) * 100)
    : 0;

  return (
    <div className="space-y-8">
      {/* Quick Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Cases Processed"
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
          label="Avg AI Confidence"
          value={usage ? `${Math.round(usage.avg_confidence * 100)}%` : "—"}
          icon={TrendingUp}
          color="bg-orange-100 text-orange-700"
        />
      </div>

      {/* Two Column: Usage + Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Usage This Month */}
        <div className="p-6 border border-[var(--border)] rounded-xl space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-bold">This Month's Usage</h2>
            <span className="text-sm text-[var(--muted-foreground)] capitalize">
              {billing?.subscription_tier || "No plan"} plan
            </span>
          </div>
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span>{billing?.usage?.extractions_used || 0} extractions used</span>
              <span>{billing?.usage?.extractions_included || 0} included</span>
            </div>
            <div className="w-full bg-[var(--muted)] rounded-full h-3">
              <div
                className={cn(
                  "h-3 rounded-full transition-all",
                  usagePct > 100 ? "bg-red-500" : usagePct > 80 ? "bg-yellow-500" : "bg-green-500"
                )}
                style={{ width: `${Math.min(100, usagePct)}%` }}
              />
            </div>
            {billing?.usage && billing.usage.overage_count > 0 && (
              <p className="text-xs text-yellow-600 mt-2">
                {billing.usage.overage_count} overage extractions this month
              </p>
            )}
          </div>
          <Link
            href="/billing"
            className="flex items-center gap-1 text-sm text-blue-600 hover:underline"
          >
            <CreditCard className="w-3.5 h-3.5" />
            Manage billing & budget
          </Link>
        </div>

        {/* Quick Actions */}
        <div className="p-6 border border-[var(--border)] rounded-xl space-y-4">
          <h2 className="font-bold">Quick Actions</h2>
          <div className="space-y-3">
            <Link
              href="/?action=upload"
              className="flex items-center justify-between p-3 bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg hover:from-blue-100 hover:to-indigo-100 transition-colors"
            >
              <div className="flex items-center gap-3">
                <Upload className="w-5 h-5 text-blue-600" />
                <div>
                  <p className="text-sm font-semibold">New Prior Auth Case</p>
                  <p className="text-xs text-[var(--muted-foreground)]">Upload a clinical note or robotic report</p>
                </div>
              </div>
              <ArrowRight className="w-4 h-4 text-blue-400" />
            </Link>
            <Link
              href="/analytics"
              className="flex items-center justify-between p-3 bg-[var(--muted)] rounded-lg hover:bg-[var(--border)] transition-colors"
            >
              <div className="flex items-center gap-3">
                <TrendingUp className="w-5 h-5 text-[var(--muted-foreground)]" />
                <div>
                  <p className="text-sm font-semibold">View Analytics</p>
                  <p className="text-xs text-[var(--muted-foreground)]">Outcomes, approval rates, time saved</p>
                </div>
              </div>
              <ArrowRight className="w-4 h-4 text-[var(--muted-foreground)]" />
            </Link>
          </div>
        </div>
      </div>

      {/* Outcome Breakdown */}
      {outcomes && outcomes.total_with_outcome > 0 && (
        <div className="p-6 border border-[var(--border)] rounded-xl space-y-4">
          <h2 className="font-bold">Prior Auth Outcomes</h2>
          <div className="grid grid-cols-4 gap-4">
            {[
              { label: "Approved", count: outcomes.approved, color: "text-green-700 bg-green-50" },
              { label: "Denied", count: outcomes.denied, color: "text-red-700 bg-red-50" },
              { label: "Pending", count: outcomes.pending, color: "text-yellow-700 bg-yellow-50" },
              { label: "Appealed", count: outcomes.appealed, color: "text-blue-700 bg-blue-50" },
            ].map((item) => (
              <div key={item.label} className={cn("p-4 rounded-lg text-center", item.color)}>
                <p className="text-2xl font-bold">{item.count}</p>
                <p className="text-xs font-medium">{item.label}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
