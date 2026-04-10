"use client";

import { useState, useCallback, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { ArrowLeft, Pencil, Check, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { NavBar } from "@/components/nav-bar";
import { FileDropzone } from "@/components/file-dropzone";
import { ProcessingStatus } from "@/components/processing-status";
import { PriorAuthForm } from "@/components/prior-auth-form";
import { AISummary } from "@/components/ai-summary";
import { CaseCard } from "@/components/case-card";
import { ReadinessScore } from "@/components/readiness-score";
import { FormSkeleton } from "@/components/skeleton";
import { NarrativePanel } from "@/components/narrative-panel";
import { TimeSaved } from "@/components/time-saved";
import { useFileUpload } from "@/hooks/use-file-upload";
import {
  getCase,
  getJobStatus,
  generateNarrative,
  uploadClinicalNoteText,
  retryJob,
  type CaseResponse,
  type NarrativeResponse,
  type JobStatusResponse,
} from "@/lib/api";

const API_BASE = "/api/proxy/api/v1";

const STATUS_COLORS: Record<string, string> = {
  open: "bg-blue-100 text-blue-700",
  submitted: "bg-yellow-100 text-yellow-700",
  approved: "bg-green-100 text-green-700",
  denied: "bg-red-100 text-red-700",
  appealed: "bg-purple-100 text-purple-700",
};

const SAMPLE_NOTE = `ORTHOPAEDIC CONSULTATION NOTE

Patient presents with severe right knee pain consistent with end-stage osteoarthritis.
Weight-bearing AP and lateral radiographs demonstrate Kellgren-Lawrence Grade IV changes
with complete loss of medial joint space, subchondral sclerosis, and large osteophyte
formation. 12-degree varus malalignment.

DIAGNOSIS: Primary osteoarthritis, right knee (ICD-10: M17.11)

CONSERVATIVE TREATMENT HISTORY:
- NSAIDs (Meloxicam 15mg daily) x 8 months - inadequate pain relief
- Physical therapy (3x/week for 8 weeks) - completed without significant improvement
- Cortisone injection (40mg triamcinolone acetonide) - temporary relief lasting 3 weeks
- Hyaluronic acid viscosupplementation (Synvisc-One) - no meaningful benefit
- Unloader brace x 6 months - minimal benefit

RECOMMENDATION:
Given failure of all reasonable conservative measures and severity of radiographic
findings with significant functional limitation, recommend right total knee arthroplasty
using the Stryker Triathlon Total Knee System with Mako robotic-assisted surgical technique.`;

interface CaseJob {
  job_id: string;
  status: string;
  source_type: string;
  original_filename: string | null;
  created_at: string | null;
}

export default function CaseDetailPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const shortId = params.shortId as string;

  const { uploads, uploadFile } = useFileUpload();
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [narrative, setNarrative] = useState<NarrativeResponse | null>(null);
  const [selectedPayer, setSelectedPayer] = useState<string | null>(null);
  const [selectedProcedure, setSelectedProcedure] = useState<string | null>(null);
  const [demoLoading, setDemoLoading] = useState(false);
  const [editingLabel, setEditingLabel] = useState(false);
  const [labelDraft, setLabelDraft] = useState("");

  // Load case data
  const { data: caseData, isLoading: caseLoading } = useQuery({
    queryKey: ["case", shortId],
    queryFn: () => getCase(shortId),
  });

  // Load jobs for this case
  const { data: caseJobs } = useQuery<CaseJob[]>({
    queryKey: ["case-jobs", caseData?.id],
    queryFn: async () => {
      if (!caseData?.id) return [];
      const res = await fetch(`${API_BASE}/ingest/jobs?limit=50`);
      if (!res.ok) return [];
      const allJobs: CaseJob[] = await res.json();
      // Filter client-side for now — backend will add case filter later
      return allJobs;
    },
    enabled: !!caseData?.id,
  });

  // Auto-select the most recent completed job
  useEffect(() => {
    if (caseJobs && caseJobs.length > 0 && !activeJobId) {
      const completed = caseJobs.find((j) => j.status === "completed");
      if (completed) setActiveJobId(completed.job_id);
    }
  }, [caseJobs, activeJobId]);

  // Load job status + extraction for the active job
  const { data: jobStatus } = useQuery<JobStatusResponse>({
    queryKey: ["job", activeJobId],
    queryFn: () => getJobStatus(activeJobId!),
    enabled: !!activeJobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "completed" || status === "failed") return false;
      return 2000;
    },
  });

  // Load most recent narrative for this extraction
  const extractionId = jobStatus?.extraction_result?.id;
  useQuery<NarrativeResponse | null>({
    queryKey: ["narrative", extractionId],
    queryFn: async () => {
      if (!extractionId) return null;
      // Try to fetch via the share endpoint which is read-only
      // For now we just rely on the narrative being set after generation
      return null;
    },
    enabled: false, // only load on demand
  });

  const narrativeMutation = useMutation({
    mutationFn: ({ extractionId, payer, procedure }: { extractionId: string; payer: string | null; procedure: string | null }) =>
      generateNarrative(extractionId, payer, procedure),
    onSuccess: (data) => setNarrative(data),
  });

  const handleFileDrop = useCallback(
    async (file: File) => {
      const response = await uploadFile(file);
      if (response) {
        setActiveJobId(response.job_id);
        setNarrative(null);
        queryClient.invalidateQueries({ queryKey: ["case-jobs"] });
        queryClient.invalidateQueries({ queryKey: ["case", shortId] });
      }
    },
    [uploadFile, queryClient, shortId],
  );

  const handleDemo = async () => {
    if (!caseData) return;
    setDemoLoading(true);
    try {
      const data = await uploadClinicalNoteText(SAMPLE_NOTE, caseData.id);
      setActiveJobId(data.job_id);
      setNarrative(null);
      queryClient.invalidateQueries({ queryKey: ["case-jobs"] });
      queryClient.invalidateQueries({ queryKey: ["case", shortId] });
    } catch {
      // silently fail
    } finally {
      setDemoLoading(false);
    }
  };

  const handleGenerateNarrative = useCallback(
    (extractionId: string, payer: string | null, procedure: string | null) => {
      narrativeMutation.mutate({ extractionId, payer, procedure });
    },
    [narrativeMutation],
  );

  const handleSaveLabel = async () => {
    if (!caseData) return;
    await fetch(`${API_BASE}/cases/${shortId}?label=${encodeURIComponent(labelDraft)}`, {
      method: "PATCH",
    });
    queryClient.invalidateQueries({ queryKey: ["case", shortId] });
    setEditingLabel(false);
  };

  const extraction = jobStatus?.extraction_result || null;
  const isProcessing = activeJobId && jobStatus?.status === "processing";

  if (caseLoading) {
    return (
      <div className="min-h-screen bg-[var(--background)]">
        <NavBar />
        <main className="max-w-7xl mx-auto p-6">
          <div className="h-8 w-48 bg-[var(--muted)] rounded animate-pulse mb-6" />
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
            <div className="lg:col-span-2 space-y-4">
              <div className="h-40 bg-[var(--muted)] rounded-lg animate-pulse" />
            </div>
            <div className="lg:col-span-3 space-y-4">
              <div className="h-64 bg-[var(--muted)] rounded-lg animate-pulse" />
            </div>
          </div>
        </main>
      </div>
    );
  }

  if (!caseData) {
    return (
      <div className="min-h-screen bg-[var(--background)]">
        <NavBar />
        <main className="max-w-5xl mx-auto p-6 text-center py-20">
          <h1 className="text-xl font-bold mb-2">Case not found</h1>
          <p className="text-[var(--muted-foreground)] mb-4">
            The case <span className="font-mono">{shortId}</span> doesn&apos;t exist or you don&apos;t have access.
          </p>
          <Link href="/cases" className="text-sm text-blue-600 hover:underline">
            Back to cases
          </Link>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--background)]">
      <NavBar />
      <main id="main-content" className="max-w-7xl mx-auto p-6">
        {/* Case Header */}
        <div className="flex items-center gap-3 mb-6">
          <Link
            href="/cases"
            className="p-1.5 rounded hover:bg-[var(--muted)] transition-colors"
            aria-label="Back to cases"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div className="flex items-center gap-2 flex-1 min-w-0">
            <span className="font-mono font-bold text-lg">{caseData.short_id}</span>
            <span className={cn("px-2 py-0.5 rounded text-[10px] font-medium capitalize", STATUS_COLORS[caseData.status] || "bg-gray-100 text-gray-700")}>
              {caseData.status}
            </span>
            {editingLabel ? (
              <div className="flex items-center gap-1 flex-1 min-w-0">
                <input
                  value={labelDraft}
                  onChange={(e) => setLabelDraft(e.target.value)}
                  className="flex-1 px-2 py-1 border border-[var(--border)] rounded text-sm min-w-0"
                  placeholder="Case label..."
                  autoFocus
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleSaveLabel();
                    if (e.key === "Escape") setEditingLabel(false);
                  }}
                />
                <button onClick={handleSaveLabel} className="p-1 rounded hover:bg-[var(--muted)]">
                  <Check className="w-3.5 h-3.5 text-green-600" />
                </button>
                <button onClick={() => setEditingLabel(false)} className="p-1 rounded hover:bg-[var(--muted)]">
                  <X className="w-3.5 h-3.5 text-red-500" />
                </button>
              </div>
            ) : (
              <button
                onClick={() => { setLabelDraft(caseData.label || ""); setEditingLabel(true); }}
                className="flex items-center gap-1 text-sm text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors truncate"
              >
                {caseData.label || "Add label..."}
                <Pencil className="w-3 h-3 flex-shrink-0" />
              </button>
            )}
          </div>
        </div>

        {/* Work Surface */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          {/* Left Panel — Documents */}
          <div className="lg:col-span-2 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold">Documents</h2>
              {caseData.document_count === 0 && (
                <button
                  onClick={handleDemo}
                  disabled={demoLoading}
                  className="text-xs px-3 py-1 rounded border border-[var(--border)] hover:bg-[var(--muted)] transition-colors disabled:opacity-50"
                >
                  {demoLoading ? "Loading..." : "Try Demo"}
                </button>
              )}
            </div>

            <FileDropzone onFileDrop={handleFileDrop} uploads={uploads} />
            <ProcessingStatus jobId={activeJobId} />

            {/* Job list for this case */}
            {caseJobs && caseJobs.length > 0 && (
              <div className="space-y-1.5">
                <h3 className="text-sm font-semibold text-[var(--muted-foreground)]">Uploaded Documents</h3>
                {caseJobs.map((job) => (
                  <button
                    key={job.job_id}
                    onClick={() => { setActiveJobId(job.job_id); setNarrative(null); }}
                    className={cn(
                      "w-full flex items-center gap-2 p-2.5 rounded-md text-left text-sm transition-colors border",
                      job.job_id === activeJobId
                        ? "border-[var(--primary)] bg-[var(--primary)]/5"
                        : "border-transparent hover:bg-[var(--muted)]"
                    )}
                  >
                    <span className={cn(
                      "w-2 h-2 rounded-full flex-shrink-0",
                      job.status === "completed" ? "bg-green-500" : job.status === "failed" ? "bg-red-500" : "bg-yellow-500"
                    )} />
                    <span className="truncate flex-1">{job.original_filename || job.source_type}</span>
                    <span className="text-xs text-[var(--muted-foreground)] capitalize">{job.source_type.replace("_", " ")}</span>
                  </button>
                ))}
              </div>
            )}

            <TimeSaved
              jobCreatedAt={jobStatus?.created_at || null}
              isComplete={jobStatus?.status === "completed"}
            />

            {jobStatus?.status === "failed" && (
              <div role="alert" className="p-3 rounded-lg bg-red-50 border border-red-200 flex items-center justify-between">
                <p className="text-sm text-red-700">{jobStatus.error_message || "Processing failed"}</p>
                <button
                  onClick={async () => { if (activeJobId) { await retryJob(activeJobId); setNarrative(null); } }}
                  className="px-3 py-1 text-xs font-medium bg-red-600 text-white rounded hover:bg-red-700"
                >
                  Retry
                </button>
              </div>
            )}
          </div>

          {/* Right Panel — Extraction + Narrative */}
          <div className="lg:col-span-3 space-y-6">
            {isProcessing ? (
              <FormSkeleton />
            ) : extraction ? (
              <>
                <CaseCard job={jobStatus} />
                <AISummary extraction={extraction} />
                <ReadinessScore
                  extraction={extraction}
                  selectedPayer={selectedPayer}
                  selectedProcedure={selectedProcedure}
                />
                <PriorAuthForm
                  extraction={extraction}
                  onGenerateNarrative={handleGenerateNarrative}
                  isGenerating={narrativeMutation.isPending}
                  selectedPayer={selectedPayer}
                  selectedProcedure={selectedProcedure}
                  onPayerChange={setSelectedPayer}
                  onProcedureChange={setSelectedProcedure}
                />
                {narrativeMutation.isError && (
                  <div className="p-3 rounded-lg bg-red-50 border border-red-200">
                    <p className="text-sm text-red-700">Narrative generation failed. Please try again.</p>
                  </div>
                )}
                <NarrativePanel
                  narrative={narrative}
                  extractionId={extraction.id}
                  onRegenerate={() => {
                    if (extraction.id)
                      narrativeMutation.mutate({
                        extractionId: extraction.id,
                        payer: selectedPayer,
                        procedure: selectedProcedure,
                      });
                  }}
                  isRegenerating={narrativeMutation.isPending}
                  onNarrativeUpdate={(text) => {
                    if (narrative) setNarrative({ ...narrative, narrative_text: text });
                  }}
                />
              </>
            ) : (
              <div className="text-center py-16 border border-dashed border-[var(--border)] rounded-xl">
                <p className="text-[var(--muted-foreground)]">
                  Upload a clinical document to get started
                </p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
