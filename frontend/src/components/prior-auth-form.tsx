"use client";

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { cn } from "@/lib/utils";
import type { ExtractionResult } from "@/lib/api";

const schema = z.object({
  diagnosis_code: z.string().min(1, "Required"),
  conservative_treatments_failed: z.string(),
  implant_type_requested: z.string(),
  robotic_assistance_required: z.boolean(),
  clinical_justification: z.string(),
});

type FormData = z.infer<typeof schema>;

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
  onGenerateNarrative: (extractionId: string) => void;
  isGenerating: boolean;
}

export function PriorAuthForm({ extraction, onGenerateNarrative, isGenerating }: PriorAuthFormProps) {
  const {
    register,
    reset,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
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
    }
  }, [extraction, reset]);

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
          <div>
            <label className="block text-sm font-medium mb-1">ICD-10 Diagnosis Code</label>
            <input
              {...register("diagnosis_code")}
              className="w-full px-3 py-2 border border-[var(--border)] rounded-md bg-[var(--background)] text-sm"
            />
            {errors.diagnosis_code && (
              <p className="text-xs text-[var(--destructive)] mt-1">{errors.diagnosis_code.message}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">
              Conservative Treatments Failed
            </label>
            <input
              {...register("conservative_treatments_failed")}
              className="w-full px-3 py-2 border border-[var(--border)] rounded-md bg-[var(--background)] text-sm"
              placeholder="NSAIDs, Physical Therapy, Cortisone Injection"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Implant Requested</label>
            <input
              {...register("implant_type_requested")}
              className="w-full px-3 py-2 border border-[var(--border)] rounded-md bg-[var(--background)] text-sm"
            />
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              {...register("robotic_assistance_required")}
              className="w-4 h-4 rounded border-[var(--border)]"
            />
            <label className="text-sm font-medium">Robotic Assistance Required</label>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Clinical Justification</label>
            <textarea
              {...register("clinical_justification")}
              rows={4}
              className="w-full px-3 py-2 border border-[var(--border)] rounded-md bg-[var(--background)] text-sm resize-y"
            />
          </div>

          <button
            type="button"
            onClick={() => onGenerateNarrative(extraction.id)}
            disabled={isGenerating}
            className={cn(
              "w-full py-3 rounded-md text-sm font-semibold transition-colors",
              "bg-[var(--primary)] text-[var(--primary-foreground)]",
              "hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
            )}
          >
            {isGenerating ? "Generating..." : "Generate Payer Submission Narrative"}
          </button>
        </form>
      )}
    </div>
  );
}
