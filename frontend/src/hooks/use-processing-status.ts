"use client";

import { useEffect, useState } from "react";
import { getSSEUrl } from "@/lib/api";

export interface ProcessingStatus {
  status: string;
  step: string;
  progress: number;
}

export function useProcessingStatus(jobId: string | null) {
  const [status, setStatus] = useState<ProcessingStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId) return;

    const es = new EventSource(getSSEUrl(jobId));

    es.addEventListener("status", (e) => {
      try {
        setStatus(JSON.parse(e.data));
      } catch {
        setError("Failed to parse status update");
      }
    });

    es.onerror = () => {
      es.close();
    };

    return () => es.close();
  }, [jobId]);

  return { status, error };
}
