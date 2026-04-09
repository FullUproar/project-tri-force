"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { FileText, ChevronDown, ChevronRight, Filter } from "lucide-react";
import { NavBar } from "@/components/nav-bar";
import { cn } from "@/lib/utils";
import {
  fetchPolicyChunks,
  fetchPayers,
  fetchProcedures,
  type PolicyChunk,
} from "@/lib/api";

// Group chunks by payer → procedure → section_title
function groupChunks(chunks: PolicyChunk[]): Map<string, Map<string, PolicyChunk[]>> {
  const grouped = new Map<string, Map<string, PolicyChunk[]>>();
  for (const chunk of chunks) {
    const procedure = chunk.procedure ?? "General";
    if (!grouped.has(chunk.payer)) {
      grouped.set(chunk.payer, new Map());
    }
    const byProcedure = grouped.get(chunk.payer)!;
    if (!byProcedure.has(procedure)) {
      byProcedure.set(procedure, []);
    }
    byProcedure.get(procedure)!.push(chunk);
  }
  return grouped;
}

function SectionGroup({ chunks }: { chunks: PolicyChunk[] }) {
  // Group by section_title within a procedure
  const bySectionMap = new Map<string, PolicyChunk[]>();
  for (const chunk of chunks) {
    const section = chunk.section_title ?? "General";
    if (!bySectionMap.has(section)) bySectionMap.set(section, []);
    bySectionMap.get(section)!.push(chunk);
  }
  const sections = Array.from(bySectionMap.entries());

  return (
    <div className="space-y-3">
      {sections.map(([section, sectionChunks]) => (
        <div key={section} className="space-y-2">
          <h4 className="text-xs font-semibold text-[var(--muted-foreground)] uppercase tracking-wide px-1">
            {section}
          </h4>
          {sectionChunks
            .sort((a, b) => a.chunk_index - b.chunk_index)
            .map((chunk) => (
              <div
                key={chunk.id}
                id={`chunk-${chunk.id}`}
                className="p-3 border border-[var(--border)] rounded-md bg-[var(--background)] text-sm leading-relaxed scroll-mt-20"
              >
                <p className="text-gray-700 whitespace-pre-wrap">{chunk.content}</p>
                <p className="mt-1.5 text-[10px] text-[var(--muted-foreground)]">
                  Chunk #{chunk.chunk_index + 1}
                </p>
              </div>
            ))}
        </div>
      ))}
    </div>
  );
}

function ProcedureAccordion({
  procedure,
  chunks,
  defaultOpen,
}: {
  procedure: string;
  chunks: PolicyChunk[];
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen ?? false);
  return (
    <div className="border border-[var(--border)] rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-4 py-3 bg-[var(--muted)] hover:bg-[var(--muted)]/80 transition-colors text-left"
        aria-expanded={open}
      >
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-[var(--muted-foreground)]" />
          <span className="text-sm font-medium">{procedure}</span>
          <span className="text-xs text-[var(--muted-foreground)]">({chunks.length} chunks)</span>
        </div>
        {open ? (
          <ChevronDown className="w-4 h-4 text-[var(--muted-foreground)]" />
        ) : (
          <ChevronRight className="w-4 h-4 text-[var(--muted-foreground)]" />
        )}
      </button>
      {open && (
        <div className="p-4">
          <SectionGroup chunks={chunks} />
        </div>
      )}
    </div>
  );
}

function PayerSection({
  payer,
  procedureMap,
}: {
  payer: string;
  procedureMap: Map<string, PolicyChunk[]>;
}) {
  const [open, setOpen] = useState(true);
  const totalChunks = Array.from(procedureMap.values()).reduce((sum, c) => sum + c.length, 0);

  return (
    <div className="space-y-3">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center gap-2 text-left group"
        aria-expanded={open}
      >
        {open ? (
          <ChevronDown className="w-4 h-4 text-[var(--muted-foreground)] group-hover:text-gray-700 transition-colors" />
        ) : (
          <ChevronRight className="w-4 h-4 text-[var(--muted-foreground)] group-hover:text-gray-700 transition-colors" />
        )}
        <h2 className="font-bold text-base">{payer}</h2>
        <span className="text-xs text-[var(--muted-foreground)] font-normal">
          {procedureMap.size} procedure{procedureMap.size !== 1 ? "s" : ""} · {totalChunks} chunks
        </span>
      </button>
      {open && (
        <div className="space-y-2 pl-6">
          {Array.from(procedureMap.entries()).map(([procedure, chunks], i) => (
            <ProcedureAccordion
              key={procedure}
              procedure={procedure}
              chunks={chunks}
              defaultOpen={i === 0 && procedureMap.size === 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function PoliciesPage() {
  const [selectedPayer, setSelectedPayer] = useState<string>("");
  const [selectedProcedure, setSelectedProcedure] = useState<string>("");

  const { data: payers } = useQuery<string[]>({
    queryKey: ["payers"],
    queryFn: fetchPayers,
  });

  const { data: procedures } = useQuery<string[]>({
    queryKey: ["procedures", selectedPayer],
    queryFn: () => fetchProcedures(selectedPayer || undefined),
  });

  const {
    data: chunks,
    isLoading,
    isError,
  } = useQuery<PolicyChunk[]>({
    queryKey: ["policy-chunks", selectedPayer, selectedProcedure],
    queryFn: () =>
      fetchPolicyChunks(selectedPayer || undefined, selectedProcedure || undefined),
  });

  const grouped = chunks ? groupChunks(chunks) : new Map<string, Map<string, PolicyChunk[]>>();
  const isEmpty = !isLoading && chunks && chunks.length === 0;

  return (
    <div className="min-h-screen bg-[var(--background)]">
      <NavBar />

      <main className="max-w-5xl mx-auto p-6 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold">Policy Documents</h1>
            <p className="text-sm text-[var(--muted-foreground)] mt-0.5">
              Browse payer policy chunks by payer and procedure
            </p>
          </div>
          {chunks && (
            <span className="text-xs text-[var(--muted-foreground)]">
              {chunks.length} chunk{chunks.length !== 1 ? "s" : ""} found
            </span>
          )}
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3 p-4 border border-[var(--border)] rounded-lg bg-[var(--muted)]">
          <div className="flex items-center gap-1.5 text-sm font-medium text-[var(--muted-foreground)]">
            <Filter className="w-4 h-4" />
            Filters
          </div>
          <select
            value={selectedPayer}
            onChange={(e) => {
              setSelectedPayer(e.target.value);
              setSelectedProcedure("");
            }}
            className="px-3 py-1.5 border border-[var(--border)] rounded-md text-sm bg-[var(--background)] min-w-[160px]"
            aria-label="Filter by payer"
          >
            <option value="">All Payers</option>
            {payers?.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
          <select
            value={selectedProcedure}
            onChange={(e) => setSelectedProcedure(e.target.value)}
            className="px-3 py-1.5 border border-[var(--border)] rounded-md text-sm bg-[var(--background)] min-w-[160px]"
            aria-label="Filter by procedure"
          >
            <option value="">All Procedures</option>
            {procedures?.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
          {(selectedPayer || selectedProcedure) && (
            <button
              onClick={() => {
                setSelectedPayer("");
                setSelectedProcedure("");
              }}
              className="px-3 py-1.5 text-xs font-medium text-[var(--muted-foreground)] hover:text-gray-700 border border-[var(--border)] rounded-md bg-[var(--background)] transition-colors"
            >
              Clear filters
            </button>
          )}
        </div>

        {/* Content */}
        {isLoading && (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-20 bg-[var(--muted)] rounded-lg animate-pulse" />
            ))}
          </div>
        )}

        {isError && (
          <div className="p-6 text-center border border-dashed border-red-200 rounded-xl bg-red-50">
            <p className="text-sm text-red-600">Failed to load policy chunks. Please try again.</p>
          </div>
        )}

        {isEmpty && (
          <div className="p-8 text-center border border-dashed border-[var(--border)] rounded-xl">
            <FileText className="w-8 h-8 text-[var(--muted-foreground)] mx-auto mb-3" />
            <p className="text-sm text-[var(--muted-foreground)]">
              {selectedPayer || selectedProcedure
                ? "No policy chunks found for the selected filters."
                : "No policy chunks have been ingested yet."}
            </p>
          </div>
        )}

        {!isLoading && !isError && grouped.size > 0 && (
          <div className="space-y-8">
            {Array.from(grouped.entries()).map(([payer, procedureMap]) => (
              <PayerSection key={payer} payer={payer} procedureMap={procedureMap} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
