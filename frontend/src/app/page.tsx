"use client";

import { useState, useCallback } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { UserButton } from "@clerk/nextjs";
import { DemoButton } from "@/components/demo-button";
import { FileDropzone } from "@/components/file-dropzone";
import { JobHistory } from "@/components/job-history";
import { ProcessingStatus } from "@/components/processing-status";
import { TimeSaved } from "@/components/time-saved";
import { PriorAuthForm } from "@/components/prior-auth-form";
import { AISummary } from "@/components/ai-summary";
import { CaseCard } from "@/components/case-card";
import { ReadinessScore } from "@/components/readiness-score";
import { FormSkeleton } from "@/components/skeleton";
import { NarrativePanel } from "@/components/narrative-panel";
import { useFileUpload } from "@/hooks/use-file-upload";
import { getJobStatus, generateNarrative, retryJob, type NarrativeResponse } from "@/lib/api";

export default function Dashboard() {
  const { uploads, uploadFile } = useFileUpload();
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [narrative, setNarrative] = useState<NarrativeResponse | null>(null);

  // Poll job status when we have an active processing job
  const { data: jobStatus } = useQuery({
    queryKey: ["job", activeJobId],
    queryFn: () => getJobStatus(activeJobId!),
    enabled: !!activeJobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "completed" || status === "failed") return false;
      return 2000;
    },
  });

  const narrativeMutation = useMutation({
    mutationFn: generateNarrative,
    onSuccess: (data) => setNarrative(data),
  });

  const handleFileDrop = useCallback(
    async (file: File) => {
      const response = await uploadFile(file);
      if (response) {
        setActiveJobId(response.job_id);
        setNarrative(null);
      }
    },
    [uploadFile]
  );

  const handleGenerateNarrative = useCallback(
    (extractionId: string) => {
      narrativeMutation.mutate(extractionId);
    },
    [narrativeMutation]
  );

  const extraction = jobStatus?.extraction_result || null;
  const isProcessing = activeJobId && jobStatus?.status === "processing";

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="border-b border-[var(--border)] px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <img src="/logo-globe.webp" alt="CortaLoom" className="w-9 h-9" />
            <div>
              <h1 className="text-xl font-bold">CortaLoom</h1>
              <p className="text-xs text-[var(--muted-foreground)]">
                ASC Prior Authorization Agent
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {activeJobId && (
              <button
                onClick={() => {
                  setActiveJobId(null);
                  setNarrative(null);
                }}
                className="text-xs px-3 py-1 rounded border border-[var(--border)] hover:bg-[var(--muted)] transition-colors"
              >
                New Case
              </button>
            )}
            <span className="text-xs px-2 py-1 bg-[var(--muted)] rounded">v0.1.0</span>
            <UserButton />
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto p-6">
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          {/* Left Column: Upload + Status */}
          <div className="lg:col-span-2 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold">Clinical Documents</h2>
              <DemoButton onJobCreated={(jobId) => { setActiveJobId(jobId); setNarrative(null); }} />
            </div>
            <FileDropzone onFileDrop={handleFileDrop} uploads={uploads} />
            <ProcessingStatus jobId={activeJobId} />
            <JobHistory
              onSelectJob={(jobId) => {
                setActiveJobId(jobId);
                setNarrative(null);
              }}
              activeJobId={activeJobId}
            />

            <TimeSaved
              jobCreatedAt={jobStatus?.created_at || null}
              isComplete={jobStatus?.status === "completed"}
            />

            {jobStatus?.status === "failed" && (
              <div className="p-3 rounded-lg bg-red-50 border border-red-200 flex items-center justify-between">
                <p className="text-sm text-red-700">{jobStatus.error_message || "Processing failed"}</p>
                <button
                  onClick={async () => {
                    if (activeJobId) {
                      await retryJob(activeJobId);
                      setNarrative(null);
                    }
                  }}
                  className="px-3 py-1 text-xs font-medium bg-red-600 text-white rounded hover:bg-red-700"
                >
                  Retry
                </button>
              </div>
            )}
          </div>

          {/* Right Column: Form + Narrative */}
          <div className="lg:col-span-3 space-y-6">
            {isProcessing ? (
              <FormSkeleton />
            ) : (
              <>
                <CaseCard job={jobStatus} />
                <AISummary extraction={extraction} />
                <ReadinessScore extraction={extraction} />
                <PriorAuthForm
                  extraction={extraction}
                  onGenerateNarrative={handleGenerateNarrative}
                  isGenerating={narrativeMutation.isPending}
                />
                <NarrativePanel
                  narrative={narrative}
                  extractionId={extraction?.id || null}
                  onRegenerate={() => {
                    if (extraction?.id) narrativeMutation.mutate(extraction.id);
                  }}
                  isRegenerating={narrativeMutation.isPending}
                />
              </>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
