"use client";

import { useState, useCallback } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { ASCHome } from "@/components/asc-home";
import { FileDropzone } from "@/components/file-dropzone";
import { JobHistory } from "@/components/job-history";
import { NavBar } from "@/components/nav-bar";
import { ProcessingStatus } from "@/components/processing-status";
import { TimeSaved } from "@/components/time-saved";
import { PriorAuthForm } from "@/components/prior-auth-form";
import { AISummary } from "@/components/ai-summary";
import { CaseCard } from "@/components/case-card";
import { ReadinessScore } from "@/components/readiness-score";
import { FormSkeleton } from "@/components/skeleton";
import { NarrativePanel } from "@/components/narrative-panel";
import { WelcomeHero } from "@/components/welcome-hero";
import { useFileUpload } from "@/hooks/use-file-upload";
import {
  getJobStatus,
  generateNarrative,
  retryJob,
  uploadClinicalNoteText,
  type NarrativeResponse,
} from "@/lib/api";

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

interface OrgInfo {
  id: string;
  name: string;
  is_admin: boolean;
}

export function Dashboard() {
  const { uploads, uploadFile } = useFileUpload();
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [narrative, setNarrative] = useState<NarrativeResponse | null>(null);
  const [demoLoading, setDemoLoading] = useState(false);
  const [demoError, setDemoError] = useState<string | null>(null);
  const [showWorkSurface, setShowWorkSurface] = useState(false);
  const [selectedPayer, setSelectedPayer] = useState<string | null>(null);
  const [selectedProcedure, setSelectedProcedure] = useState<string | null>(null);

  const { data: orgInfo } = useQuery<OrgInfo>({
    queryKey: ["me"],
    queryFn: async () => {
      const res = await fetch("/api/proxy/api/v1/me");
      if (!res.ok) return { id: "", name: "", is_admin: false };
      return res.json();
    },
  });

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
      }
    },
    [uploadFile]
  );

  const handleDemo = async () => {
    setDemoLoading(true);
    setDemoError(null);
    try {
      const data = await uploadClinicalNoteText(SAMPLE_NOTE);
      setActiveJobId(data.job_id);
      setNarrative(null);
    } catch {
      setDemoError("Failed to load demo. Please try again.");
    } finally {
      setDemoLoading(false);
    }
  };

  const handleGenerateNarrative = useCallback(
    (extractionId: string, payer: string | null, procedure: string | null) => {
      narrativeMutation.mutate({ extractionId, payer, procedure });
    },
    [narrativeMutation]
  );

  const handleNewCase = () => {
    setActiveJobId(null);
    setNarrative(null);
    setSelectedPayer(null);
    setSelectedProcedure(null);
  };

  const extraction = jobStatus?.extraction_result || null;
  const isProcessing = activeJobId && jobStatus?.status === "processing";
  const showWelcome = !activeJobId && uploads.length === 0;

  // ASC users see their home dashboard first, then work surface when they click "New Case"
  const isASC = orgInfo && !orgInfo.is_admin;
  const showASCHome = isASC && !showWorkSurface && !activeJobId && uploads.length === 0;

  return (
    <div className="min-h-screen">
      <NavBar />
      <main id="main-content" className="max-w-7xl mx-auto p-6">
        {showASCHome ? (
          <div className="space-y-6">
            <ASCHome />
            <div className="text-center">
              <button
                onClick={() => setShowWorkSurface(true)}
                className="px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg font-semibold hover:from-blue-700 hover:to-indigo-700"
              >
                Start New Prior Auth Case
              </button>
            </div>
          </div>
        ) : (
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          {showWelcome && !isASC && (
            <WelcomeHero onTryDemo={handleDemo} isDemoLoading={demoLoading} />
          )}
          {demoError && (
            <div className="lg:col-span-5">
              <p className="text-sm text-red-600 bg-red-50 p-3 rounded-lg border border-red-200">{demoError}</p>
            </div>
          )}
          <div className="lg:col-span-2 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold">Clinical Documents</h2>
              {activeJobId && (
                <button
                  onClick={handleNewCase}
                  className="text-xs px-3 py-1 rounded border border-[var(--border)] hover:bg-[var(--muted)] transition-colors"
                >
                  New Case
                </button>
              )}
            </div>
            <FileDropzone onFileDrop={handleFileDrop} uploads={uploads} />
            <ProcessingStatus jobId={activeJobId} />
            <JobHistory
              onSelectJob={(jobId) => { setActiveJobId(jobId); setNarrative(null); }}
              activeJobId={activeJobId}
            />
            <TimeSaved
              jobCreatedAt={jobStatus?.created_at || null}
              isComplete={jobStatus?.status === "completed"}
            />
            {jobStatus?.status === "failed" && (
              <div role="alert" aria-live="assertive" className="p-3 rounded-lg bg-red-50 border border-red-200 flex items-center justify-between">
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
          <div className="lg:col-span-3 space-y-6">
            {isProcessing ? (
              <FormSkeleton />
            ) : (
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
                    <p className="text-sm text-red-700">
                      Narrative generation failed. Please try again.
                    </p>
                  </div>
                )}
                <NarrativePanel
                  narrative={narrative}
                  extractionId={extraction?.id || null}
                  onRegenerate={() => {
                    if (extraction?.id)
                      narrativeMutation.mutate({
                        extractionId: extraction.id,
                        payer: selectedPayer,
                        procedure: selectedProcedure,
                      });
                  }}
                  isRegenerating={narrativeMutation.isPending}
                  onNarrativeUpdate={(text) => {
                    if (narrative) {
                      setNarrative({ ...narrative, narrative_text: text });
                    }
                  }}
                />
              </>
            )}
          </div>
        </div>
        )}
      </main>
    </div>
  );
}
