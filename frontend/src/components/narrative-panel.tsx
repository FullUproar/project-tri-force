"use client";

import { useState } from "react";
import DOMPurify from "dompurify";
import { Copy, Check, RefreshCw, Download, Link2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { exportNarrativePdf, type NarrativeResponse } from "@/lib/api";

interface NarrativePanelProps {
  narrative: NarrativeResponse | null;
  extractionId: string | null;
  onRegenerate: () => void;
  isRegenerating: boolean;
}

export function NarrativePanel({ narrative, extractionId, onRegenerate, isRegenerating }: NarrativePanelProps) {
  const [copied, setCopied] = useState(false);
  const [linkCopied, setLinkCopied] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  if (!narrative) return null;

  const handleCopy = async () => {
    await navigator.clipboard.writeText(narrative.narrative_text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = async () => {
    if (!extractionId) return;
    setDownloading(true);
    setDownloadError(null);
    try {
      await exportNarrativePdf(extractionId);
    } catch {
      setDownloadError("PDF export failed. You can copy the text instead.");
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="space-y-3 p-4 border border-[var(--border)] rounded-lg">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-bold">Payer Submission Narrative</h3>
          {narrative.payer && (
            <span className="px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-700">
              {narrative.payer}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-[var(--muted-foreground)]">
            {narrative.model_used} ({narrative.prompt_version})
          </span>
          <button
            onClick={async () => {
              if (!extractionId) return;
              const url = `${window.location.origin}/api/proxy/api/v1/share/${extractionId}`;
              await navigator.clipboard.writeText(url);
              setLinkCopied(true);
              setTimeout(() => setLinkCopied(false), 2000);
            }}
            disabled={!extractionId}
            className="p-1.5 rounded hover:bg-[var(--muted)] transition-colors disabled:opacity-50"
            title="Copy share link"
            aria-label="Copy share link"
          >
            {linkCopied ? (
              <Check className="w-4 h-4 text-[var(--success)]" />
            ) : (
              <Link2 className="w-4 h-4" />
            )}
          </button>
          <button
            onClick={handleDownload}
            disabled={downloading || !extractionId}
            className="p-1.5 rounded hover:bg-[var(--muted)] transition-colors disabled:opacity-50"
            title="Download PDF"
            aria-label="Download PDF"
          >
            <Download className={cn("w-4 h-4", downloading && "animate-pulse")} />
          </button>
          <button
            onClick={handleCopy}
            className="p-1.5 rounded hover:bg-[var(--muted)] transition-colors"
            title="Copy to clipboard"
            aria-label="Copy to clipboard"
          >
            {copied ? (
              <Check className="w-4 h-4 text-[var(--success)]" />
            ) : (
              <Copy className="w-4 h-4" />
            )}
          </button>
          <button
            onClick={onRegenerate}
            disabled={isRegenerating}
            className="p-1.5 rounded hover:bg-[var(--muted)] transition-colors disabled:opacity-50"
            title="Regenerate"
            aria-label="Regenerate narrative"
          >
            <RefreshCw className={cn("w-4 h-4", isRegenerating && "animate-spin")} />
          </button>
        </div>
      </div>

      {downloadError && (
        <p className="text-xs text-red-600 bg-red-50 p-2 rounded">{downloadError}</p>
      )}

      <div
        aria-live="polite"
        className="prose prose-sm max-w-none text-sm leading-relaxed bg-[var(--muted)] p-4 rounded-md"
        dangerouslySetInnerHTML={{
          __html: DOMPurify.sanitize(
            narrative.narrative_text
              .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
              .replace(/\n\n/g, "</p><p>")
              .replace(/\n/g, "<br>")
              .replace(/^/, "<p>")
              .replace(/$/, "</p>")
          ),
        }}
      />
    </div>
  );
}
