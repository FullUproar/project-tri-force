"use client";

import { FileText, Image, Stethoscope, Calendar } from "lucide-react";
import { cn } from "@/lib/utils";
import { getICD10Description } from "@/lib/icd10";
import type { ExtractionResult, JobStatusResponse } from "@/lib/api";

interface CaseCardProps {
  job: JobStatusResponse | undefined;
}

function SourceIcon({ type }: { type: string }) {
  if (type === "dicom") return <Image className="w-4 h-4 text-purple-600" />;
  if (type === "robotic_report") return <FileText className="w-4 h-4 text-red-600" />;
  return <Stethoscope className="w-4 h-4 text-blue-600" />;
}

function SourceLabel({ type }: { type: string }) {
  const labels: Record<string, string> = {
    dicom: "DICOM Imaging",
    clinical_note: "Clinical Note",
    robotic_report: "Robotic Report",
  };
  return <>{labels[type] || type}</>;
}

function StatusPill({ status }: { status: string }) {
  const styles: Record<string, string> = {
    completed: "bg-green-100 text-green-800",
    processing: "bg-yellow-100 text-yellow-800",
    pending: "bg-gray-100 text-gray-800",
    failed: "bg-red-100 text-red-800",
  };
  return (
    <span className={cn("px-2 py-0.5 rounded-full text-xs font-semibold capitalize", styles[status] || styles.pending)}>
      {status}
    </span>
  );
}

function OutcomePill({ outcome }: { outcome: string | null | undefined }) {
  if (!outcome) return null;
  const styles: Record<string, string> = {
    approved: "bg-green-100 text-green-800 border-green-300",
    denied: "bg-red-100 text-red-800 border-red-300",
    pending: "bg-yellow-100 text-yellow-800 border-yellow-300",
    appealed: "bg-blue-100 text-blue-800 border-blue-300",
  };
  return (
    <span className={cn("px-2 py-0.5 rounded-full text-xs font-semibold capitalize border", styles[outcome] || "")}>
      {outcome}
    </span>
  );
}

export function CaseCard({ job }: CaseCardProps) {
  if (!job) return null;

  const ext = job.extraction_result;
  const icdDesc = ext?.diagnosis_code ? getICD10Description(ext.diagnosis_code) : null;

  return (
    <div className="border border-[var(--border)] rounded-xl overflow-hidden">
      {/* Card Header */}
      <div className="px-5 py-3 bg-[var(--muted)] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <SourceIcon type={job.source_type} />
          <span className="text-sm font-semibold">
            <SourceLabel type={job.source_type} />
          </span>
        </div>
        <div className="flex items-center gap-2">
          <OutcomePill outcome={ext?.outcome} />
          <StatusPill status={job.status} />
        </div>
      </div>

      {/* Card Body */}
      {ext && (
        <div className="px-5 py-4 space-y-3">
          {/* Diagnosis Row */}
          <div className="flex items-baseline gap-2">
            <span className="text-lg font-bold font-mono">{ext.diagnosis_code}</span>
            {icdDesc && (
              <span className="text-sm text-blue-600">{icdDesc}</span>
            )}
          </div>

          {/* Quick Stats */}
          <div className="grid grid-cols-3 gap-3">
            <div className="text-center p-2 bg-[var(--muted)] rounded-lg">
              <p className="text-xl font-bold">{ext.conservative_treatments_failed?.length || 0}</p>
              <p className="text-xs text-[var(--muted-foreground)]">Treatments Failed</p>
            </div>
            <div className="text-center p-2 bg-[var(--muted)] rounded-lg">
              <p className="text-xl font-bold">{ext.robotic_assistance_required ? "Yes" : "No"}</p>
              <p className="text-xs text-[var(--muted-foreground)]">Robotic Assist</p>
            </div>
            <div className="text-center p-2 bg-[var(--muted)] rounded-lg">
              <p className="text-xl font-bold">{Math.round((ext.confidence_score || 0) * 100)}%</p>
              <p className="text-xs text-[var(--muted-foreground)]">AI Confidence</p>
            </div>
          </div>

          {/* Implant */}
          {ext.implant_type_requested && ext.implant_type_requested !== "Not specified" && (
            <div className="text-sm">
              <span className="font-medium">Implant: </span>
              <span className="text-[var(--muted-foreground)]">{ext.implant_type_requested}</span>
            </div>
          )}

          {/* Timestamp */}
          <div className="flex items-center gap-1 text-xs text-[var(--muted-foreground)]">
            <Calendar className="w-3 h-3" />
            {job.created_at && new Date(job.created_at).toLocaleString()}
          </div>
        </div>
      )}
    </div>
  );
}
