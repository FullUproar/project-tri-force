"use client";

import { CheckCircle2 } from "lucide-react";

interface TreatmentChecklistProps {
  treatments: string[] | null;
}

export function TreatmentChecklist({ treatments }: TreatmentChecklistProps) {
  if (!treatments || treatments.length === 0) return null;

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium">
        Conservative Treatments Failed ({treatments.length})
      </label>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {treatments.map((treatment, i) => (
          <div
            key={i}
            className="flex items-center gap-2 p-2.5 bg-red-50 border border-red-200 rounded-md"
          >
            <CheckCircle2 className="w-4 h-4 text-red-500 flex-shrink-0" />
            <span className="text-sm text-red-800">{treatment}</span>
          </div>
        ))}
      </div>
      <p className="text-xs text-[var(--muted-foreground)]">
        All listed treatments attempted and failed — supports medical necessity
      </p>
    </div>
  );
}
