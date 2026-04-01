"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Shield, ShieldCheck, Building2 } from "lucide-react";
import { cn } from "@/lib/utils";

const API_BASE = "/api/proxy/api/v1";

interface Org {
  id: string;
  name: string;
  is_active: boolean;
  baa_signed_at: string | null;
  job_count: number;
  extraction_count: number;
}

async function fetchOrgs(): Promise<Org[]> {
  const res = await fetch(`${API_BASE}/admin/organizations`);
  if (!res.ok) return [];
  return res.json();
}

async function createOrg(name: string) {
  const res = await fetch(`${API_BASE}/admin/organizations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

async function signBaa(orgId: string) {
  const res = await fetch(`${API_BASE}/admin/organizations/${orgId}/sign-baa`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export default function AdminPage() {
  const queryClient = useQueryClient();
  const [newOrgName, setNewOrgName] = useState("");
  const [createdKey, setCreatedKey] = useState<string | null>(null);

  const { data: orgs } = useQuery({
    queryKey: ["admin-orgs"],
    queryFn: fetchOrgs,
    refetchInterval: 10000,
  });

  const createMutation = useMutation({
    mutationFn: createOrg,
    onSuccess: (data) => {
      setCreatedKey(data.api_key);
      setNewOrgName("");
      queryClient.invalidateQueries({ queryKey: ["admin-orgs"] });
    },
  });

  const baaMutation = useMutation({
    mutationFn: signBaa,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-orgs"] }),
  });

  return (
    <div className="min-h-screen bg-[var(--background)]">
      <header className="border-b border-[var(--border)] px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center gap-3">
          <img src="/logo-globe.webp" alt="CortaLoom" className="w-9 h-9" />
          <div>
            <h1 className="text-xl font-bold">CortaLoom Admin</h1>
            <p className="text-xs text-[var(--muted-foreground)]">
              Pilot Organization Management
            </p>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto p-6 space-y-6">
        {/* Create New Org */}
        <div className="p-5 border border-[var(--border)] rounded-lg space-y-3">
          <h2 className="font-semibold flex items-center gap-2">
            <Plus className="w-4 h-4" /> New ASC Organization
          </h2>
          <div className="flex gap-3">
            <input
              value={newOrgName}
              onChange={(e) => setNewOrgName(e.target.value)}
              placeholder="e.g., Springfield Orthopaedic ASC"
              className="flex-1 px-3 py-2 border border-[var(--border)] rounded-md text-sm bg-[var(--background)]"
            />
            <button
              onClick={() => newOrgName.trim() && createMutation.mutate(newOrgName.trim())}
              disabled={!newOrgName.trim() || createMutation.isPending}
              className="px-4 py-2 bg-[var(--primary)] text-[var(--primary-foreground)] rounded-md text-sm font-medium disabled:opacity-50"
            >
              Create
            </button>
          </div>
          {createdKey && (
            <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-md">
              <p className="text-xs font-semibold text-yellow-800">
                API Key (copy now — shown only once):
              </p>
              <code className="text-xs break-all text-yellow-900 select-all">{createdKey}</code>
            </div>
          )}
        </div>

        {/* Org List */}
        <div className="space-y-3">
          <h2 className="font-semibold flex items-center gap-2">
            <Building2 className="w-4 h-4" /> Organizations ({orgs?.length || 0})
          </h2>
          {orgs?.map((org) => (
            <div
              key={org.id}
              className="p-4 border border-[var(--border)] rounded-lg flex items-center justify-between"
            >
              <div>
                <h3 className="font-medium">{org.name}</h3>
                <div className="flex items-center gap-4 mt-1 text-xs text-[var(--muted-foreground)]">
                  <span>{org.job_count} jobs</span>
                  <span>{org.extraction_count} extractions</span>
                  <span className="flex items-center gap-1">
                    {org.baa_signed_at ? (
                      <>
                        <ShieldCheck className="w-3 h-3 text-[var(--success)]" />
                        BAA signed
                      </>
                    ) : (
                      <>
                        <Shield className="w-3 h-3 text-[var(--warning)]" />
                        BAA pending
                      </>
                    )}
                  </span>
                </div>
              </div>
              {!org.baa_signed_at && (
                <button
                  onClick={() => baaMutation.mutate(org.id)}
                  disabled={baaMutation.isPending}
                  className="px-3 py-1.5 text-xs font-medium border border-[var(--success)] text-[var(--success)] rounded-md hover:bg-green-50 disabled:opacity-50"
                >
                  Sign BAA
                </button>
              )}
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
