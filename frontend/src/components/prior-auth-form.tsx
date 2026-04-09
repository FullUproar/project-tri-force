"use client";

import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { useQuery } from "@tanstack/react-query";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { cn } from "@/lib/utils";
import { updateOutcome, fetchPayers, fetchProcedures, type ExtractionResult, type PriorAuthOutcome } from "@/lib/api";
import { getICD10Description } from "@/lib/icd10";
import { TreatmentChecklist } from "@/components/treatment-checklist";

const schema = z.object({
  diagnosis_code: z.string().min(1, "Required"),
  conservative_treatments_failed: z.string(),
  implant_type_requested: z.string(),
  robotic_assistance_required: z.boolean(),
  clinical_justification: z.string(),
});

type FormData = z.infer<typeof schema>;

// ICD-10 prefix to suggested procedure (mirrors backend logic)
const ICD10_TO_PROCEDURE: Record<string, string> = {
  M17: "Total Knee Replacement",
  M16: "Total Hip Replacement",
  M75: "Rotator Cuff Repair",
  M54: "Lumbar Fusion",
  M47: "Lumbar Fusion",
  M51: "Lumbar Fusion",
  M48: "Lumbar Fusion",
  G89: "Spinal Cord Stimulator",
};

function suggestProcedure(diagnosisCode: string | null): string | null {
  if (!diagnosisCode) return null;
  const prefix = diagnosisCode.includes(".")
    ? diagnosisCode.split(".")[0]
    : diagnosisCode.slice(0, 3);
  return ICD10_TO_PROCEDURE[prefix] || null;
}

function ConfidenceBadge({ score }: { score: number | null }) {
  if (score === null) return null;
  const color =
    score >= 0.8
      ? "bg-green-100 text-green-700"
      : score >= 0.5
        ? "bg-yellow-100 text-yellow-700"
        : "bg-red-100 text-red-700";
  return (
    <span className={cn("px-2 py-0.5 rounded text-xs font-medium", color)}>
      {Math.round(score * 100)}% confidence
    </span>
  );
}

interface PriorAuthFormProps {
  extraction: ExtractionResult | null;
  onGenerateNarrative: (extractionId: string, payer: string | null, procedure: string | null) => void;
  isGenerating: boolean;
  selectedPayer: string | null;
  selectedProcedure: string | null;
  onPayerChange: (payer: string | null) => void;
  onProcedureChange: (procedure: string | null) => void;
}

export function PriorAuthForm({
  extraction,
  onGenerateNarrative,
  isGenerating,
  selectedPayer,
  selectedProcedure,
  onPayerChange,
  onProcedureChange,
}: PriorAuthFormProps) {
  const {
    register,
    reset,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const { data: payers } = useQuery({
    queryKey: ["payers"],
    queryFn: fetchPayers,
    staleTime: 5 * 60 * 1000,
  });

  const { data: procedures } = useQuery({
    queryKey: ["procedures", selectedPayer],
    queryFn: () => fetchProcedures(selectedPayer || undefined),
    enabled: !!selectedPayer,
    staleTime: 5 * 60 * 1000,
  });

  useEffect(() => {
    if (extraction) {
      reset({
        diagnosis_code: extraction.diagnosis_code || "",
        conservative_treatments_failed:
          extraction.conservative_treatments_failed?.join(", ") || "",
        implant_type_requested: extraction.implant_type_requested || "",
        robotic_assistance_required: extraction.robotic_assistance_required || false,
        clinical_justification: extraction.clinical_justification || "",
      });
      // Auto-suggest procedure from diagnosis code
      if (!selectedProcedure) {
        const suggested = suggestProcedure(extraction.diagnosis_code);
        if (suggested) onProcedureChange(suggested);
      }
    }
  }, [extraction, reset, selectedProcedure, onProcedureChange]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold">Prior Authorization Data</h2>
        {extraction && <ConfidenceBadge score={extraction.confidence_score} />}
      </div>

      {!extraction ? (
        <div className="p-8 text-center text-[var(--muted-foreground)] border border-dashed border-[var(--border)] rounded-lg">
          <p className="text-sm">Upload a clinical document to auto-populate this form</p>
        </div>
      ) : (
        <form className="space-y-4">
          {/* Payer Selection */}
          <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg space-y-3">
            <p className="text-sm font-bold text-blue-900">Target Payer</p>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="payer-select" className="block text-xs font-medium text-blue-800 mb-1">Insurance Company</label>
                <select
                  id="payer-select"
                  value={selectedPayer || ""}
                  onChange={(e) => {
                    onPayerChange(e.target.value || null);
                    onProcedureChange(null);
                  }}
                  className="w-full px-3 py-2 border border-blue-300 rounded-md bg-white text-sm"
                >
                  <option value="">Select payer...</option>
                  {payers?.map((p) => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </select>
              </div>
              <div>
                <label htmlFor="procedure-select" className="block text-xs font-medium text-blue-800 mb-1">Procedure</label>
                <select
                  id="procedure-select"
                  value={selectedProcedure || ""}
                  onChange={(e) => onProcedureChange(e.target.value || null)}
                  className="w-full px-3 py-2 border border-blue-300 rounded-md bg-white text-sm"
                >
                  <option value="">Select procedure...</option>
                  {procedures?.map((p) => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </select>
              </div>
            </div>
            {selectedPayer && selectedProcedure && (
              <p className="text-xs text-blue-700">
                Narrative will be tailored to {selectedPayer}&apos;s specific requirements for {selectedProcedure}
              </p>
            )}
            {selectedPayer && !selectedProcedure && (
              <p className="text-xs text-blue-600">
                Select a procedure to unlock payer-specific narrative generation
              </p>
            )}
          </div>

          <div>
            <label htmlFor="diagnosis_code" className="block text-sm font-medium mb-1">ICD-10 Diagnosis Code</label>
            <input
              id="diagnosis_code"
              {...register("diagnosis_code")}
              className="w-full px-3 py-2 border border-[var(--border)] rounded-md bg-[var(--background)] text-sm"
            />
            {errors.diagnosis_code && (
              <p className="text-xs text-[var(--destructive)] mt-1">{errors.diagnosis_code.message}</p>
            )}
            {extraction?.diagnosis_code && getICD10Description(extraction.diagnosis_code) && (
              <p className="text-xs text-blue-600 mt-1">
                {getICD10Description(extraction.diagnosis_code)}
              </p>
            )}
          </div>

          <TreatmentChecklist treatments={extraction.conservative_treatments_failed} />

          <div>
            <label htmlFor="implant_type_requested" className="block text-sm font-medium mb-1">Implant Requested</label>
            <input
              id="implant_type_requested"
              {...register("implant_type_requested")}
              className="w-full px-3 py-2 border border-[var(--border)] rounded-md bg-[var(--background)] text-sm"
            />
          </div>

          <div className="flex items-center gap-2">
            <input
              id="robotic_assistance_required"
              type="checkbox"
              {...register("robotic_assistance_required")}
              className="w-4 h-4 rounded border-[var(--border)]"
            />
            <label htmlFor="robotic_assistance_required" className="text-sm font-medium">Robotic Assistance Required</label>
          </div>

          <div>
            <label htmlFor="clinical_justification" className="block text-sm font-medium mb-1">Clinical Justification</label>
            <textarea
              id="clinical_justification"
              {...register("clinical_justification")}
              rows={4}
              className="w-full px-3 py-2 border border-[var(--border)] rounded-md bg-[var(--background)] text-sm resize-y"
            />
          </div>

          {/* Outcome Tracker */}
          <div>
            <label className="block text-sm font-medium mb-2">Prior Auth Outcome</label>
            <div className="flex gap-2">
              {(["pending", "approved", "denied", "appealed"] as PriorAuthOutcome[]).map((o) => {
                const colors: Record<string, string> = {
                  pending: "border-yellow-400 bg-yellow-50 text-yellow-700",
                  approved: "border-green-400 bg-green-50 text-green-700",
                  denied: "border-red-400 bg-red-50 text-red-700",
                  appealed: "border-blue-400 bg-blue-50 text-blue-700",
                };
                const isActive = extraction.outcome === o;
                return (
                  <button
                    key={o}
                    type="button"
                    onClick={() => updateOutcome(extraction.id, o)}
                    className={cn(
                      "px-3 py-1.5 rounded-md text-xs font-medium border transition-all capitalize",
                      isActive ? colors[o] + " ring-2 ring-offset-1" : "border-[var(--border)] text-[var(--muted-foreground)] hover:bg-[var(--muted)]"
                    )}
                  >
                    {o}
                  </button>
                );
              })}
            </div>
          </div>

          <button
            type="button"
            onClick={() => onGenerateNarrative(extraction.id, selectedPayer, selectedProcedure)}
            disabled={isGenerating}
            className={cn(
              "w-full py-3 rounded-md text-sm font-semibold transition-colors",
              "bg-[var(--primary)] text-[var(--primary-foreground)]",
              "hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
            )}
          >
            {isGenerating
              ? "Generating..."
              : selectedPayer
                ? `Generate ${selectedPayer}-Specific Narrative`
                : "Generate Payer Submission Narrative"}
          </button>
        </form>
      )}
    </div>
  );
}
