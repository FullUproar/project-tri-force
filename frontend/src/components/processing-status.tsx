"use client";

import { useProcessingStatus } from "@/hooks/use-processing-status";
import { cn } from "@/lib/utils";

const STEP_LABELS: Record<string, string> = {
  phi_scrubbing: "Removing PHI...",
  llm_extraction: "Extracting clinical data...",
  saving_results: "Saving results...",
  done: "Complete",
  error: "Failed",
};

interface ProcessingStatusProps {
  jobId: string | null;
}

export function ProcessingStatus({ jobId }: ProcessingStatusProps) {
  const { status } = useProcessingStatus(jobId);

  if (!jobId || !status) return null;

  const isComplete = status.status === "completed";
  const isFailed = status.status === "failed";
  const percentage = Math.round(status.progress * 100);

  return (
    <div className="p-4 rounded-lg bg-[var(--muted)] space-y-2">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium">
          {STEP_LABELS[status.step] || status.step}
        </span>
        <span
          className={cn(
            "text-xs font-semibold",
            isComplete && "text-[var(--success)]",
            isFailed && "text-[var(--destructive)]"
          )}
        >
          {percentage}%
        </span>
      </div>
      <div className="w-full bg-[var(--border)] rounded-full h-2">
        <div
          className={cn(
            "h-2 rounded-full transition-all duration-500",
            isComplete
              ? "bg-[var(--success)]"
              : isFailed
                ? "bg-[var(--destructive)]"
                : "bg-[var(--primary)]"
          )}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}
