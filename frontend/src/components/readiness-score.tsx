"use client";

import { cn } from "@/lib/utils";
import type { ExtractionResult } from "@/lib/api";

interface ReadinessScoreProps {
  extraction: ExtractionResult | null;
}

interface Gap {
  label: string;
  met: boolean;
  tip: string;
}

function analyzeReadiness(ext: ExtractionResult): { score: number; gaps: Gap[] } {
  const gaps: Gap[] = [
    {
      label: "ICD-10 diagnosis code",
      met: !!ext.diagnosis_code && ext.diagnosis_code !== "Not found",
      tip: "Ensure the clinical note includes a specific ICD-10 code",
    },
    {
      label: "3+ conservative treatments failed",
      met: (ext.conservative_treatments_failed?.length || 0) >= 3,
      tip: "Most payers require at least 3 failed conservative treatments",
    },
    {
      label: "Treatment durations documented",
      met: ext.conservative_treatments_failed?.some((t) =>
        /\d+\s*(week|month|day|wk|mo)/i.test(t)
      ) || false,
      tip: "Include durations (e.g., 'PT x 8 weeks') — payers deny without timeframes",
    },
    {
      label: "Implant specified",
      met: !!ext.implant_type_requested && ext.implant_type_requested !== "Not specified",
      tip: "Specifying the exact implant system strengthens the request",
    },
    {
      label: "Clinical justification",
      met: !!ext.clinical_justification && ext.clinical_justification.length > 50,
      tip: "A detailed clinical justification reduces denial risk",
    },
    {
      label: "Imaging referenced",
      met: /x-ray|radiograph|mri|ct scan|imaging|kellgren/i.test(
        ext.clinical_justification || ""
      ),
      tip: "Payers require recent imaging evidence — ensure the note references imaging findings",
    },
    {
      label: "High AI confidence",
      met: (ext.confidence_score || 0) >= 0.8,
      tip: "Low confidence may indicate missing information in the source note",
    },
  ];

  const metCount = gaps.filter((g) => g.met).length;
  const score = Math.round((metCount / gaps.length) * 100);
  return { score, gaps };
}

export function ReadinessScore({ extraction }: ReadinessScoreProps) {
  if (!extraction) return null;

  const { score, gaps } = analyzeReadiness(extraction);
  const unmet = gaps.filter((g) => !g.met);

  const color =
    score >= 80
      ? "text-green-700 bg-green-50 border-green-200"
      : score >= 60
        ? "text-yellow-700 bg-yellow-50 border-yellow-200"
        : "text-red-700 bg-red-50 border-red-200";

  const barColor =
    score >= 80 ? "bg-green-500" : score >= 60 ? "bg-yellow-500" : "bg-red-500";

  return (
    <div className={cn("p-4 rounded-lg border", color)}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-bold">Payer Readiness Score</span>
        <span className="text-lg font-bold">{score}%</span>
      </div>
      <div className="w-full bg-white/50 rounded-full h-2 mb-3">
        <div
          className={cn("h-2 rounded-full transition-all", barColor)}
          style={{ width: `${score}%` }}
        />
      </div>
      {unmet.length > 0 && (
        <div className="space-y-1">
          <p className="text-xs font-semibold">Gaps to address:</p>
          {unmet.map((gap, i) => (
            <p key={i} className="text-xs opacity-80">
              • {gap.label} — {gap.tip}
            </p>
          ))}
        </div>
      )}
      {unmet.length === 0 && (
        <p className="text-xs font-medium">All payer requirements met — ready to submit</p>
      )}
    </div>
  );
}
