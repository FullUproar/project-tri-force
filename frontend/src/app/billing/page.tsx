"use client";

import { useQuery, useMutation } from "@tanstack/react-query";
import { CreditCard, CheckCircle2, AlertCircle, ExternalLink } from "lucide-react";
import { cn } from "@/lib/utils";

const API_BASE = "/api/proxy/api/v1";

interface BillingStatus {
  organization: string;
  subscription_status: string;
  stripe_customer_id: string | null;
}

export default function BillingPage() {
  const { data: billing } = useQuery<BillingStatus>({
    queryKey: ["billing-status"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/billing/status`);
      if (!res.ok) throw new Error("Failed to fetch billing");
      return res.json();
    },
  });

  const checkoutMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch(`${API_BASE}/billing/checkout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          success_url: `${window.location.origin}/billing?status=success`,
          cancel_url: `${window.location.origin}/billing?status=cancel`,
        }),
      });
      if (!res.ok) throw new Error("Failed to create checkout");
      return res.json();
    },
    onSuccess: (data) => {
      window.location.href = data.checkout_url;
    },
  });

  const portalMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch(`${API_BASE}/billing/portal`, { method: "POST" });
      if (!res.ok) throw new Error("Failed to open portal");
      return res.json();
    },
    onSuccess: (data) => {
      window.location.href = data.portal_url;
    },
  });

  const status = billing?.subscription_status || "none";
  const isActive = status === "active" || status === "trialing";

  const statusConfig: Record<string, { icon: React.ElementType; color: string; label: string }> = {
    active: { icon: CheckCircle2, color: "text-green-600 bg-green-50 border-green-200", label: "Active" },
    trialing: { icon: CheckCircle2, color: "text-blue-600 bg-blue-50 border-blue-200", label: "Trial" },
    past_due: { icon: AlertCircle, color: "text-yellow-600 bg-yellow-50 border-yellow-200", label: "Past Due" },
    canceled: { icon: AlertCircle, color: "text-red-600 bg-red-50 border-red-200", label: "Canceled" },
    none: { icon: CreditCard, color: "text-gray-600 bg-gray-50 border-gray-200", label: "No Subscription" },
  };

  const config = statusConfig[status] || statusConfig.none;
  const StatusIcon = config.icon;

  return (
    <div className="min-h-screen bg-[var(--background)]">
      <header className="border-b border-[var(--border)] px-6 py-4">
        <div className="max-w-3xl mx-auto flex items-center gap-3">
          <img src="/logo-globe.webp" alt="CortaLoom" className="w-9 h-9" />
          <div>
            <h1 className="text-xl font-bold">Billing</h1>
            <p className="text-xs text-[var(--muted-foreground)]">
              Manage your CortaLoom subscription
            </p>
          </div>
        </div>
      </header>

      <main className="max-w-3xl mx-auto p-6 space-y-6">
        {/* Current Status */}
        <div className={cn("p-6 rounded-xl border flex items-center gap-4", config.color)}>
          <StatusIcon className="w-8 h-8 flex-shrink-0" />
          <div>
            <p className="font-bold text-lg">{config.label}</p>
            {billing && <p className="text-sm opacity-80">{billing.organization}</p>}
          </div>
        </div>

        {/* Pricing Card */}
        {!isActive && (
          <div className="p-6 border border-[var(--border)] rounded-xl space-y-4">
            <div>
              <h2 className="text-lg font-bold">CortaLoom ASC Plan</h2>
              <p className="text-sm text-[var(--muted-foreground)]">
                Everything your ASC needs for AI-powered prior authorization
              </p>
            </div>
            <div className="flex items-baseline gap-1">
              <span className="text-4xl font-bold">$299</span>
              <span className="text-[var(--muted-foreground)]">/month per location</span>
            </div>
            <ul className="space-y-2 text-sm">
              {[
                "Unlimited prior auth extractions",
                "AI-generated payer narratives",
                "PDF export for payer submission",
                "DICOM, PDF, and clinical note ingestion",
                "PHI scrubbing (HIPAA compliant)",
                "Outcome tracking and analytics",
                "Dedicated support",
              ].map((feature) => (
                <li key={feature} className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0" />
                  {feature}
                </li>
              ))}
            </ul>
            <button
              onClick={() => checkoutMutation.mutate()}
              disabled={checkoutMutation.isPending}
              className="w-full py-3 bg-[var(--primary)] text-[var(--primary-foreground)] rounded-lg font-semibold hover:opacity-90 disabled:opacity-50"
            >
              {checkoutMutation.isPending ? "Redirecting to Stripe..." : "Subscribe Now"}
            </button>
          </div>
        )}

        {/* Manage Subscription */}
        {isActive && (
          <div className="p-6 border border-[var(--border)] rounded-xl space-y-4">
            <h2 className="font-bold">Manage Subscription</h2>
            <p className="text-sm text-[var(--muted-foreground)]">
              Update payment method, view invoices, or cancel your subscription.
            </p>
            <button
              onClick={() => portalMutation.mutate()}
              disabled={portalMutation.isPending}
              className="flex items-center gap-2 px-4 py-2 border border-[var(--border)] rounded-lg text-sm font-medium hover:bg-[var(--muted)]"
            >
              <ExternalLink className="w-4 h-4" />
              {portalMutation.isPending ? "Opening..." : "Open Billing Portal"}
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
