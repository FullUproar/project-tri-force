"use client";

import { useQuery } from "@tanstack/react-query";
import { cn } from "@/lib/utils";
import { checkPayerReadiness, type ExtractionResult, type PayerReadinessResponse } from "@/lib/api";

interface ReadinessScoreProps {
  extraction: ExtractionResult | null;
  selectedPayer: string | null;
  selectedProcedure: string | null;
}

interface Gap {
  label: string;
  met: boolean;
  tip: string;
}

function analyzeGenericReadiness(ext: ExtractionResult): { score: number; gaps: Gap[] } {
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

function PayerSpecificReadiness({ data }: { data: PayerReadinessResponse }) {
  const score = data.readiness_score;
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
      <div className="flex items-center justify-between mb-1">
        <span className="text-sm font-bold">{data.payer} Readiness Score</span>
        <span className="text-lg font-bold">{score}%</span>
      </div>
      <p className="text-xs opacity-70 mb-2">{data.procedure}</p>
      <div className="w-full bg-white/50 rounded-full h-2 mb-3">
        <div
          className={cn("h-2 rounded-full transition-all", barColor)}
          style={{ width: `${score}%` }}
        />
      </div>
      {data.gaps.length > 0 ? (
        <div className="space-y-1">
          <p className="text-xs font-semibold">{data.payer}-specific gaps:</p>
          {data.gaps.map((gap, i) => (
            <p key={i} className="text-xs opacity-80">
              {"\u2022"} {gap}
            </p>
          ))}
        </div>
      ) : (
        <p className="text-xs font-medium">All {data.payer} requirements met — ready to submit</p>
      )}
      {data.submission_portal && data.submission_portal !== "Unknown" && (
        <p className="text-xs mt-2 opacity-70">
          Submit via: <span className="font-medium">{data.submission_portal}</span>
        </p>
      )}
    </div>
  );
}

export function ReadinessScore({ extraction, selectedPayer, selectedProcedure }: ReadinessScoreProps) {
  if (!extraction) return null;

  const hasImaging = /x-ray|radiograph|mri|ct scan|imaging|kellgren/i.test(
    extraction.clinical_justification || ""
  );

  const { data: payerReadiness } = useQuery({
    queryKey: ["payer-readiness", selectedPayer, selectedProcedure, extraction.id],
    queryFn: () =>
      checkPayerReadiness(
        selectedPayer!,
        selectedProcedure!,
        extraction.conservative_treatments_failed?.length || 0,
        hasImaging,
        0,
      ),
    enabled: !!selectedPayer && !!selectedProcedure,
    staleTime: 30_000,
  });

  // Show payer-specific readiness if available, otherwise generic
  if (payerReadiness && "readiness_score" in payerReadiness) {
    return <PayerSpecificReadiness data={payerReadiness} />;
  }

  // Generic readiness (no payer selected)
  const { score, gaps } = analyzeGenericReadiness(extraction);
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
      {!selectedPayer && (
        <p className="text-xs opacity-60 mb-2">Select a payer above for payer-specific requirements</p>
      )}
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
              {"\u2022"} {gap.label} — {gap.tip}
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
