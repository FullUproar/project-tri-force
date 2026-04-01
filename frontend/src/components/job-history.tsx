"use client";

import { useQuery } from "@tanstack/react-query";
import { cn } from "@/lib/utils";
import { FileText, Image } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || "";

interface Job {
  job_id: string;
  status: string;
  source_type: string;
  original_filename: string | null;
  created_at: string | null;
}

async function fetchJobs(): Promise<Job[]> {
  const res = await fetch(`${API_URL}/api/v1/ingest/jobs?limit=10`, {
    headers: API_KEY ? { "X-API-Key": API_KEY } : {},
  });
  if (!res.ok) return [];
  return res.json();
}

function StatusDot({ status }: { status: string }) {
  const color = {
    completed: "bg-[var(--success)]",
    processing: "bg-[var(--warning)]",
    pending: "bg-[var(--warning)]",
    failed: "bg-[var(--destructive)]",
  }[status] || "bg-gray-400";

  return <span className={cn("inline-block w-2 h-2 rounded-full", color)} />;
}

function SourceIcon({ type }: { type: string }) {
  if (type === "dicom") return <Image className="w-3.5 h-3.5 text-purple-500" />;
  return <FileText className="w-3.5 h-3.5 text-blue-500" />;
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

interface JobHistoryProps {
  onSelectJob: (jobId: string) => void;
  activeJobId: string | null;
}

export function JobHistory({ onSelectJob, activeJobId }: JobHistoryProps) {
  const { data: jobs } = useQuery({
    queryKey: ["job-history"],
    queryFn: fetchJobs,
    refetchInterval: 10000,
  });

  if (!jobs || jobs.length === 0) return null;

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold">Recent Jobs</h3>
      <div className="space-y-1">
        {jobs.map((job) => (
          <button
            key={job.job_id}
            onClick={() => onSelectJob(job.job_id)}
            className={cn(
              "w-full flex items-center gap-2 p-2 rounded-md text-left text-sm transition-colors",
              job.job_id === activeJobId
                ? "bg-[var(--primary)] text-[var(--primary-foreground)]"
                : "hover:bg-[var(--muted)]"
            )}
          >
            <SourceIcon type={job.source_type} />
            <span className="truncate flex-1">
              {job.original_filename || job.source_type}
            </span>
            <StatusDot status={job.status} />
            {job.created_at && (
              <span className="text-xs opacity-60 whitespace-nowrap">
                {timeAgo(job.created_at)}
              </span>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
