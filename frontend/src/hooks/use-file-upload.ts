"use client";

import { useState } from "react";
import {
  uploadDicom,
  uploadClinicalNote,
  uploadRoboticReport,
  type IngestionResponse,
} from "@/lib/api";

export interface UploadState {
  file: File;
  status: "uploading" | "processing" | "completed" | "failed";
  jobId?: string;
  response?: IngestionResponse;
  error?: string;
}

function getUploadFn(file: File) {
  const ext = file.name.split(".").pop()?.toLowerCase();
  if (ext === "dcm") return uploadDicom;
  if (ext === "pdf") return uploadRoboticReport;
  return uploadClinicalNote;
}

export function useFileUpload() {
  const [uploads, setUploads] = useState<UploadState[]>([]);

  const uploadFile = async (file: File) => {
    const idx = uploads.length;
    setUploads((prev) => [...prev, { file, status: "uploading" }]);

    try {
      const uploadFn = getUploadFn(file);
      const response = await uploadFn(file);

      setUploads((prev) =>
        prev.map((u, i) =>
          i === idx
            ? {
                ...u,
                status: response.status === "completed" ? "completed" : "processing",
                jobId: response.job_id,
                response,
              }
            : u
        )
      );

      return response;
    } catch (err) {
      setUploads((prev) =>
        prev.map((u, i) =>
          i === idx
            ? { ...u, status: "failed", error: err instanceof Error ? err.message : "Upload failed" }
            : u
        )
      );
      return null;
    }
  };

  const clearUploads = () => setUploads([]);

  return { uploads, uploadFile, clearUploads };
}
