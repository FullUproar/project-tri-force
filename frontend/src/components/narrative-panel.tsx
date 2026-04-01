"use client";

import { useState } from "react";
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

  if (!narrative) return null;

  const handleCopy = async () => {
    await navigator.clipboard.writeText(narrative.narrative_text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = async () => {
    if (!extractionId) return;
    setDownloading(true);
    try {
      await exportNarrativePdf(extractionId);
    } catch {
      // silently fail — user can copy text instead
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="space-y-3 p-4 border border-[var(--border)] rounded-lg">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-bold">Payer Submission Narrative</h3>
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
          >
            <Download className={cn("w-4 h-4", downloading && "animate-pulse")} />
          </button>
          <button
            onClick={handleCopy}
            className="p-1.5 rounded hover:bg-[var(--muted)] transition-colors"
            title="Copy to clipboard"
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
          >
            <RefreshCw className={cn("w-4 h-4", isRegenerating && "animate-spin")} />
          </button>
        </div>
      </div>

      <div
        className="prose prose-sm max-w-none text-sm leading-relaxed bg-[var(--muted)] p-4 rounded-md"
        dangerouslySetInnerHTML={{
          __html: narrative.narrative_text
            .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
            .replace(/\n\n/g, "</p><p>")
            .replace(/\n/g, "<br>")
            .replace(/^/, "<p>")
            .replace(/$/, "</p>"),
        }}
      />
    </div>
  );
}
