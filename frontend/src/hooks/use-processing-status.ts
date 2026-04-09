"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getSSEUrl } from "@/lib/api";

export interface ProcessingStatus {
  status: string;
  step: string;
  progress: number;
}

const MAX_RETRIES = 5;
const BASE_DELAY_MS = 1000;

export function useProcessingStatus(jobId: string | null) {
  const [status, setStatus] = useState<ProcessingStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const retriesRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const esRef = useRef<EventSource | null>(null);

  const connect = useCallback((id: string) => {
    const es = new EventSource(getSSEUrl(id));
    esRef.current = es;

    es.addEventListener("status", (e) => {
      try {
        const parsed = JSON.parse(e.data);
        setStatus(parsed);
        retriesRef.current = 0; // reset on success

        // Stop reconnecting once terminal
        if (parsed.status === "completed" || parsed.status === "failed") {
          es.close();
        }
      } catch {
        setError("Failed to parse status update");
      }
    });

    es.onerror = () => {
      es.close();
      if (retriesRef.current < MAX_RETRIES) {
        const delay = BASE_DELAY_MS * Math.pow(2, retriesRef.current);
        retriesRef.current += 1;
        timerRef.current = setTimeout(() => connect(id), delay);
      } else {
        setError("Connection lost. Please refresh to check status.");
      }
    };
  }, []);

  useEffect(() => {
    if (!jobId) return;

    retriesRef.current = 0;
    setError(null);
    connect(jobId);

    return () => {
      esRef.current?.close();
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [jobId, connect]);

  return { status, error };
}
