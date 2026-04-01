"use client";

import { useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, FileText, Image, FileWarning } from "lucide-react";
import { cn } from "@/lib/utils";
import type { UploadState } from "@/hooks/use-file-upload";

const ACCEPT = {
  "application/dicom": [".dcm"],
  "application/pdf": [".pdf"],
  "text/plain": [".txt"],
};

function StatusBadge({ status }: { status: UploadState["status"] }) {
  const colors = {
    uploading: "bg-blue-100 text-blue-700",
    processing: "bg-yellow-100 text-yellow-700",
    completed: "bg-green-100 text-green-700",
    failed: "bg-red-100 text-red-700",
  };
  return (
    <span className={cn("px-2 py-0.5 rounded text-xs font-medium", colors[status])}>
      {status}
    </span>
  );
}

function FileIcon({ name }: { name: string }) {
  const ext = name.split(".").pop()?.toLowerCase();
  if (ext === "dcm") return <Image className="w-4 h-4 text-purple-500" />;
  if (ext === "pdf") return <FileText className="w-4 h-4 text-red-500" />;
  return <FileText className="w-4 h-4 text-blue-500" />;
}

interface FileDropzoneProps {
  onFileDrop: (file: File) => void;
  uploads: UploadState[];
}

export function FileDropzone({ onFileDrop, uploads }: FileDropzoneProps) {
  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      acceptedFiles.forEach((file) => onFileDrop(file));
    },
    [onFileDrop]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPT,
    multiple: true,
  });

  return (
    <div className="space-y-4">
      <div
        {...getRootProps()}
        className={cn(
          "border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors",
          isDragActive
            ? "border-[var(--primary)] bg-blue-50"
            : "border-[var(--border)] hover:border-[var(--primary)]"
        )}
      >
        <input {...getInputProps()} />
        <Upload className="w-10 h-10 mx-auto mb-3 text-[var(--muted-foreground)]" />
        <p className="text-sm font-medium">
          {isDragActive ? "Drop files here..." : "Drop clinical files here, or click to browse"}
        </p>
        <p className="text-xs text-[var(--muted-foreground)] mt-1">
          Supports DICOM (.dcm), PDF robotic reports, and text clinical notes
        </p>
      </div>

      {uploads.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold">Uploaded Files</h3>
          {uploads.map((upload, i) => (
            <div
              key={i}
              className="flex items-center justify-between p-3 rounded-lg bg-[var(--muted)]"
            >
              <div className="flex items-center gap-2">
                <FileIcon name={upload.file.name} />
                <span className="text-sm truncate max-w-[200px]">{upload.file.name}</span>
                <span className="text-xs text-[var(--muted-foreground)]">
                  ({(upload.file.size / 1024).toFixed(1)} KB)
                </span>
              </div>
              <StatusBadge status={upload.status} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
