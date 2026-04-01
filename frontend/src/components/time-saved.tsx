"use client";

import { Clock } from "lucide-react";

interface TimeSavedProps {
  jobCreatedAt: string | null;
  isComplete: boolean;
}

export function TimeSaved({ jobCreatedAt, isComplete }: TimeSavedProps) {
  if (!isComplete || !jobCreatedAt) return null;

  const created = new Date(jobCreatedAt);
  const now = new Date();
  const processingSeconds = Math.round((now.getTime() - created.getTime()) / 1000);

  // Average manual prior auth takes 45-60 minutes per MGMA data
  const manualMinutes = 45;
  const savedMinutes = manualMinutes - Math.ceil(processingSeconds / 60);

  return (
    <div className="flex items-center gap-3 p-4 bg-gradient-to-r from-green-50 to-emerald-50 border border-green-200 rounded-lg">
      <Clock className="w-8 h-8 text-green-600 flex-shrink-0" />
      <div>
        <p className="text-sm font-bold text-green-800">
          ~{savedMinutes} minutes saved
        </p>
        <p className="text-xs text-green-600">
          Processed in {processingSeconds}s — manual prior auth averages {manualMinutes} min (MGMA)
        </p>
      </div>
    </div>
  );
}
