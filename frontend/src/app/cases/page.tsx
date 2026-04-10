"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Plus, FolderOpen, FileText, Clock, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { NavBar } from "@/components/nav-bar";
import { createCase, listCases, type CaseResponse } from "@/lib/api";

const STATUS_COLORS: Record<string, string> = {
  open: "bg-blue-100 text-blue-700",
  submitted: "bg-yellow-100 text-yellow-700",
  approved: "bg-green-100 text-green-700",
  denied: "bg-red-100 text-red-700",
  appealed: "bg-purple-100 text-purple-700",
};

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 30) return `${days}d ago`;
  return `${Math.floor(days / 30)}mo ago`;
}

export default function CasesPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<string | undefined>();

  const { data: cases, isLoading } = useQuery({
    queryKey: ["cases", statusFilter],
    queryFn: () => listCases(statusFilter),
  });

  const createMutation = useMutation({
    mutationFn: () => createCase(),
    onSuccess: (newCase) => {
      queryClient.invalidateQueries({ queryKey: ["cases"] });
      router.push(`/cases/${newCase.short_id}`);
    },
  });

  return (
    <div className="min-h-screen bg-[var(--background)]">
      <NavBar />
      <main id="main-content" className="max-w-5xl mx-auto p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">Cases</h1>
            <p className="text-sm text-[var(--muted-foreground)]">
              Prior authorization cases for your organization
            </p>
          </div>
          <button
            onClick={() => createMutation.mutate()}
            disabled={createMutation.isPending}
            className="flex items-center gap-2 px-4 py-2.5 bg-[var(--primary)] text-[var(--primary-foreground)] rounded-lg text-sm font-semibold hover:opacity-90 disabled:opacity-50 transition-opacity"
          >
            <Plus className="w-4 h-4" />
            {createMutation.isPending ? "Creating..." : "New Case"}
          </button>
        </div>

        {/* Status Filters */}
        <div className="flex gap-2 mb-6">
          {[
            { value: undefined, label: "All" },
            { value: "open", label: "Open" },
            { value: "submitted", label: "Submitted" },
            { value: "approved", label: "Approved" },
            { value: "denied", label: "Denied" },
            { value: "appealed", label: "Appealed" },
          ].map((filter) => (
            <button
              key={filter.label}
              onClick={() => setStatusFilter(filter.value)}
              className={cn(
                "px-3 py-1.5 rounded-md text-xs font-medium transition-colors",
                statusFilter === filter.value
                  ? "bg-[var(--primary)] text-[var(--primary-foreground)]"
                  : "bg-[var(--muted)] text-[var(--muted-foreground)] hover:bg-[var(--border)]"
              )}
            >
              {filter.label}
            </button>
          ))}
        </div>

        {/* Case List */}
        {isLoading ? (
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-20 bg-[var(--muted)] rounded-lg animate-pulse" />
            ))}
          </div>
        ) : !cases || cases.length === 0 ? (
          <div className="text-center py-16 border border-dashed border-[var(--border)] rounded-xl">
            <FolderOpen className="w-12 h-12 mx-auto text-[var(--muted-foreground)] mb-4" />
            <h3 className="text-lg font-semibold mb-1">No cases yet</h3>
            <p className="text-sm text-[var(--muted-foreground)] mb-4">
              Create your first case to start a prior authorization
            </p>
            <button
              onClick={() => createMutation.mutate()}
              disabled={createMutation.isPending}
              className="px-4 py-2 bg-[var(--primary)] text-[var(--primary-foreground)] rounded-lg text-sm font-semibold hover:opacity-90 disabled:opacity-50"
            >
              <Plus className="w-4 h-4 inline mr-1" />
              New Case
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            {cases.map((c) => (
              <Link
                key={c.id}
                href={`/cases/${c.short_id}`}
                className="flex items-center gap-4 p-4 border border-[var(--border)] rounded-lg hover:border-[var(--primary)] hover:bg-[var(--muted)] transition-colors group"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-mono font-bold text-sm">{c.short_id}</span>
                    <span className={cn("px-2 py-0.5 rounded text-[10px] font-medium capitalize", STATUS_COLORS[c.status] || "bg-gray-100 text-gray-700")}>
                      {c.status}
                    </span>
                  </div>
                  {c.label && (
                    <p className="text-sm text-[var(--foreground)] truncate">{c.label}</p>
                  )}
                  <div className="flex items-center gap-3 mt-1 text-xs text-[var(--muted-foreground)]">
                    <span className="flex items-center gap-1">
                      <FileText className="w-3 h-3" />
                      {c.document_count} {c.document_count === 1 ? "document" : "documents"}
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {timeAgo(c.created_at)}
                    </span>
                  </div>
                </div>
                <ChevronRight className="w-4 h-4 text-[var(--muted-foreground)] group-hover:text-[var(--primary)] transition-colors" />
              </Link>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
