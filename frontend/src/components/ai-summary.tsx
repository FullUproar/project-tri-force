"use client";

import DOMPurify from "dompurify";
import { Sparkles } from "lucide-react";
import { getICD10Description } from "@/lib/icd10";
import type { ExtractionResult } from "@/lib/api";

interface AISummaryProps {
  extraction: ExtractionResult | null;
}

export function AISummary({ extraction }: AISummaryProps) {
  if (!extraction) return null;

  const icdDesc = extraction.diagnosis_code
    ? getICD10Description(extraction.diagnosis_code) || extraction.diagnosis_code
    : "unspecified condition";

  const treatmentCount = extraction.conservative_treatments_failed?.length || 0;
  const treatments = extraction.conservative_treatments_failed?.join(", ") || "none documented";

  const implant =
    extraction.implant_type_requested && extraction.implant_type_requested !== "Not specified"
      ? extraction.implant_type_requested
      : null;

  const robotic = extraction.robotic_assistance_required;

  const parts = [
    `The AI identified <strong>${icdDesc}</strong> (${extraction.diagnosis_code}).`,
    treatmentCount > 0
      ? `The patient has failed <strong>${treatmentCount} conservative treatment${treatmentCount > 1 ? "s" : ""}</strong>: ${treatments}.`
      : "No conservative treatments were documented in the source note.",
    implant
      ? `The requesting procedure uses the <strong>${implant}</strong>${robotic ? " with <strong>robotic assistance</strong>" : ""}.`
      : robotic
        ? "Robotic-assisted surgery is indicated."
        : null,
  ].filter(Boolean);

  return (
    <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
      <div className="flex items-center gap-2 mb-2">
        <Sparkles className="w-4 h-4 text-blue-600" />
        <span className="text-sm font-bold text-blue-800">What the AI Found</span>
      </div>
      <p
        className="text-sm text-blue-900 leading-relaxed"
        dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(parts.join(" ")) }}
      />
    </div>
  );
}
