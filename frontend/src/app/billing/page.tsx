"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, AlertCircle, ExternalLink, Zap } from "lucide-react";
import { cn } from "@/lib/utils";
import { NavBar } from "@/components/nav-bar";

const API_BASE = "/api/proxy/api/v1";

interface BillingStatus {
  organization: string;
  subscription_status: string;
  subscription_tier: string | null;
  stripe_customer_id: string | null;
  overage_budget_cap: number | null;
  usage: {
    extractions_used: number;
    extractions_included: number;
    overage_count: number;
    overage_cost: number;
    budget_remaining: number | null;
    budget_exhausted: boolean;
  };
}

interface TierInfo {
  name: string;
  amount: number;
  included_extractions: number;
  description: string;
  overage_rate: number;
}

const TIER_ORDER = ["starter", "professional", "enterprise"];

function BudgetCapControl({ currentCap }: { currentCap: number | null }) {
  const [editing, setEditing] = useState(false);
  const [capValue, setCapValue] = useState(currentCap?.toString() || "");
  const queryClient = useQueryClient();

  const saveMutation = useMutation({
    mutationFn: async (cap: number | null) => {
      const res = await fetch(`${API_BASE}/billing/budget`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ budget_cap: cap }),
      });
      if (!res.ok) throw new Error("Failed");
      return res.json();
    },
    onSuccess: () => {
      setEditing(false);
      queryClient.invalidateQueries({ queryKey: ["billing-status"] });
    },
  });

  return (
    <div className="p-3 bg-[var(--muted)] rounded-lg space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">Monthly Overage Budget Cap</span>
        {!editing && (
          <button onClick={() => setEditing(true)} className="text-xs text-blue-600 hover:underline">
            {currentCap ? "Edit" : "Set limit"}
          </button>
        )}
      </div>
      {!editing ? (
        <p className="text-xs text-[var(--muted-foreground)]">
          {currentCap ? `$${currentCap.toFixed(2)}/month — extractions blocked when reached` : "No limit set — overages are unlimited"}
        </p>
      ) : (
        <div className="flex gap-2">
          <div className="flex items-center gap-1 flex-1">
            <span className="text-sm">$</span>
            <input
              value={capValue}
              onChange={(e) => setCapValue(e.target.value)}
              placeholder="e.g., 50.00"
              className="flex-1 px-2 py-1 border border-[var(--border)] rounded text-sm bg-[var(--background)]"
            />
          </div>
          <button
            onClick={() => saveMutation.mutate(capValue ? parseFloat(capValue) : null)}
            disabled={saveMutation.isPending}
            className="px-3 py-1 bg-[var(--primary)] text-[var(--primary-foreground)] rounded text-xs font-medium"
          >
            Save
          </button>
          <button
            onClick={() => { saveMutation.mutate(null); setCapValue(""); }}
            className="px-3 py-1 border border-[var(--border)] rounded text-xs"
          >
            Remove
          </button>
        </div>
      )}
    </div>
  );
}

function TierCard({
  tierId,
  tier,
  isActive,
  onSelect,
  isLoading,
}: {
  tierId: string;
  tier: TierInfo;
  isActive: boolean;
  onSelect: (tier: string) => void;
  isLoading: boolean;
}) {
  const isPro = tierId === "professional";

  return (
    <div
      className={cn(
        "p-6 border rounded-xl space-y-4 relative",
        isActive
          ? "border-green-400 bg-green-50/50 ring-2 ring-green-200"
          : isPro
            ? "border-blue-400 bg-blue-50/30"
            : "border-[var(--border)]"
      )}
    >
      {isPro && !isActive && (
        <span className="absolute -top-3 left-4 px-2 py-0.5 bg-blue-600 text-white text-xs font-bold rounded">
          Most Popular
        </span>
      )}
      {isActive && (
        <span className="absolute -top-3 left-4 px-2 py-0.5 bg-green-600 text-white text-xs font-bold rounded">
          Current Plan
        </span>
      )}
      <div>
        <h3 className="font-bold text-lg">{tier.name}</h3>
        <p className="text-xs text-[var(--muted-foreground)]">{tier.description}</p>
      </div>
      <div className="flex items-baseline gap-1">
        <span className="text-3xl font-bold">${tier.amount}</span>
        <span className="text-sm text-[var(--muted-foreground)]">/mo</span>
      </div>
      <ul className="space-y-1.5 text-sm">
        <li className="flex items-center gap-2">
          <Zap className="w-3.5 h-3.5 text-blue-500" />
          <strong>{tier.included_extractions}</strong> extractions/month
        </li>
        <li className="flex items-center gap-2">
          <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />
          AI narrative generation
        </li>
        <li className="flex items-center gap-2">
          <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />
          PDF export + share links
        </li>
        <li className="flex items-center gap-2">
          <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />
          HIPAA compliant
        </li>
        <li className="text-xs text-[var(--muted-foreground)]">
          + ${tier.overage_rate.toFixed(2)}/extraction over limit
        </li>
      </ul>
      {!isActive && (
        <button
          onClick={() => onSelect(tierId)}
          disabled={isLoading}
          className={cn(
            "w-full py-2.5 rounded-lg font-semibold text-sm",
            isPro
              ? "bg-blue-600 text-white hover:bg-blue-700"
              : "bg-[var(--primary)] text-[var(--primary-foreground)] hover:opacity-90",
            "disabled:opacity-50"
          )}
        >
          {isLoading ? "Redirecting..." : "Subscribe"}
        </button>
      )}
    </div>
  );
}

export default function BillingPage() {
  const { data: billing } = useQuery<BillingStatus>({
    queryKey: ["billing-status"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/billing/status`);
      if (!res.ok) throw new Error("Failed");
      return res.json();
    },
  });

  const { data: tiers } = useQuery<Record<string, TierInfo>>({
    queryKey: ["billing-tiers"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/billing/tiers`);
      if (!res.ok) throw new Error("Failed");
      return res.json();
    },
  });

  const checkoutMutation = useMutation({
    mutationFn: async (tier: string) => {
      const res = await fetch(`${API_BASE}/billing/checkout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tier,
          success_url: `${window.location.origin}/billing?status=success`,
          cancel_url: `${window.location.origin}/billing?status=cancel`,
        }),
      });
      if (!res.ok) throw new Error("Failed");
      return res.json();
    },
    onSuccess: (data) => {
      window.location.href = data.checkout_url;
    },
  });

  const portalMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch(`${API_BASE}/billing/portal`, { method: "POST" });
      if (!res.ok) throw new Error("Failed");
      return res.json();
    },
    onSuccess: (data) => {
      window.location.href = data.portal_url;
    },
  });

  const isActive = billing?.subscription_status === "active" || billing?.subscription_status === "trialing";
  const usage = billing?.usage;

  return (
    <div className="min-h-screen bg-[var(--background)]">
      <NavBar />

      <main className="max-w-5xl mx-auto p-6 space-y-8">
        {/* Usage Bar (active subscribers) */}
        {isActive && usage && (
          <div className="p-5 border border-[var(--border)] rounded-xl space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="font-bold">Monthly Usage</h2>
              <span className="text-sm text-[var(--muted-foreground)]">
                {usage.extractions_used} / {usage.extractions_included} extractions
              </span>
            </div>
            <div className="w-full bg-[var(--muted)] rounded-full h-3">
              <div
                className={cn(
                  "h-3 rounded-full transition-all",
                  usage.extractions_used > usage.extractions_included
                    ? "bg-red-500"
                    : usage.extractions_used > usage.extractions_included * 0.8
                      ? "bg-yellow-500"
                      : "bg-green-500"
                )}
                style={{
                  width: `${Math.min(100, (usage.extractions_used / Math.max(1, usage.extractions_included)) * 100)}%`,
                }}
              />
            </div>
            {usage.overage_count > 0 && (
              <div className="flex items-center gap-2 text-sm text-yellow-700 bg-yellow-50 p-2 rounded-md">
                <AlertCircle className="w-4 h-4" />
                {usage.overage_count} overage extractions (${usage.overage_cost.toFixed(2)} additional)
              </div>
            )}
            {/* Budget Cap */}
            <BudgetCapControl currentCap={billing?.overage_budget_cap ?? null} />

            <button
              onClick={() => portalMutation.mutate()}
              disabled={portalMutation.isPending}
              className="flex items-center gap-2 text-sm text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              {portalMutation.isPending ? "Opening..." : "Manage subscription in Stripe"}
            </button>
          </div>
        )}

        {/* Tier Cards */}
        <div>
          <h2 className="text-xl font-bold mb-1">
            {isActive ? "Your Plan" : "Choose Your Plan"}
          </h2>
          <p className="text-sm text-[var(--muted-foreground)] mb-6">
            All plans include HIPAA-compliant AI extraction, narrative generation, PDF export, and analytics.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {tiers &&
              TIER_ORDER.map((tierId) => {
                const tier = tiers[tierId];
                if (!tier) return null;
                return (
                  <TierCard
                    key={tierId}
                    tierId={tierId}
                    tier={tier}
                    isActive={billing?.subscription_tier === tierId}
                    onSelect={(t) => checkoutMutation.mutate(t)}
                    isLoading={checkoutMutation.isPending}
                  />
                );
              })}
          </div>
        </div>
      </main>
    </div>
  );
}
