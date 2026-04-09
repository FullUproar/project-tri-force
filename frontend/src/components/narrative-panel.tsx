"use client";

import { useState } from "react";
import DOMPurify from "dompurify";
import { Copy, Check, RefreshCw, Download, Link2, BookOpen } from "lucide-react";
import { cn } from "@/lib/utils";
import { exportNarrativePdf, type NarrativeResponse, type Citation } from "@/lib/api";

interface NarrativePanelProps {
  narrative: NarrativeResponse | null;
  extractionId: string | null;
  onRegenerate: () => void;
  isRegenerating: boolean;
}

function buildCitationMap(citations: Citation[]): Map<string, Citation> {
  const map = new Map<string, Citation>();
  for (const c of citations) {
    map.set(c.marker, c);
  }
  return map;
}

function renderNarrativeWithCitations(
  text: string,
  citationMap: Map<string, Citation>,
  activeCitation: string | null,
  onActivate: (marker: string | null) => void,
): React.ReactNode[] {
  // Split on [N] citation patterns, keeping the delimiters
  const parts = text.split(/(\[\d+\])/g);
  return parts.map((part, i) => {
    const match = part.match(/^\[(\d+)\]$/);
    if (match) {
      const marker = match[1];
      const citation = citationMap.get(marker);
      const isActive = activeCitation === marker;
      return (
        <span key={i} className="relative inline-block">
          <sup
            className={cn(
              "citation-marker cursor-pointer px-0.5 font-semibold text-blue-600 hover:text-blue-800 transition-colors",
              isActive && "text-blue-800 underline",
            )}
            data-citation={marker}
            onClick={() => onActivate(isActive ? null : marker)}
            title={citation ? citation.claim : `Citation ${marker}`}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === "Enter" && onActivate(isActive ? null : marker)}
            aria-label={`Citation ${marker}${citation ? `: ${citation.claim}` : ""}`}
          >
            [{marker}]
          </sup>
          {isActive && citation && (
            <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 z-10 w-72 rounded-lg border border-[var(--border)] bg-white shadow-lg p-3 text-xs text-left pointer-events-none">
              <span className="block font-semibold text-gray-800 mb-1">{citation.claim}</span>
              <span
                className={cn(
                  "inline-block px-1.5 py-0.5 rounded text-[10px] font-medium mb-1",
                  citation.source_type === "policy"
                    ? "bg-blue-100 text-blue-700"
                    : citation.source_type === "clinical"
                      ? "bg-green-100 text-green-700"
                      : "bg-gray-100 text-gray-700",
                )}
              >
                {citation.source_type}
              </span>
              {citation.section_title && (
                <span className="block text-gray-500 mb-1">{citation.section_title}</span>
              )}
              {citation.source_text && (
                <span className="block text-gray-600 italic line-clamp-3">{citation.source_text}</span>
              )}
            </span>
          )}
        </span>
      );
    }

    // Regular text — apply the same markdown transforms as before but return as dangerouslySetInnerHTML
    // We need to split further on paragraphs and render plain text segments
    return (
      <span
        key={i}
        dangerouslySetInnerHTML={{
          __html: DOMPurify.sanitize(
            part
              .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
              .replace(/\n\n/g, "</p><p>")
              .replace(/\n/g, "<br>"),
          ),
        }}
      />
    );
  });
}

const SOURCE_TYPE_COLORS: Record<string, string> = {
  policy: "bg-blue-100 text-blue-700",
  clinical: "bg-green-100 text-green-700",
  imaging: "bg-purple-100 text-purple-700",
  robotic: "bg-orange-100 text-orange-700",
};

export function NarrativePanel({ narrative, extractionId, onRegenerate, isRegenerating }: NarrativePanelProps) {
  const [copied, setCopied] = useState(false);
  const [linkCopied, setLinkCopied] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [activeCitation, setActiveCitation] = useState<string | null>(null);

  if (!narrative) return null;

  const citations = narrative.citations ?? [];
  const citationMap = buildCitationMap(citations);
  const hasCitations = citations.length > 0;

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

      {hasCitations ? (
        <div
          aria-live="polite"
          className="prose prose-sm max-w-none text-sm leading-relaxed bg-[var(--muted)] p-4 rounded-md"
          onClick={() => setActiveCitation(null)}
        >
          <p>
            {renderNarrativeWithCitations(narrative.narrative_text, citationMap, activeCitation, setActiveCitation)}
          </p>
        </div>
      ) : (
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
                .replace(/$/, "</p>"),
            ),
          }}
        />
      )}

      {hasCitations && (
        <div className="space-y-2 pt-2 border-t border-[var(--border)]">
          <h4 className="text-xs font-semibold text-[var(--muted-foreground)] flex items-center gap-1.5 uppercase tracking-wide">
            <BookOpen className="w-3.5 h-3.5" />
            Sources
          </h4>
          <ol className="space-y-2">
            {citations.map((citation) => (
              <li
                key={citation.marker}
                id={`citation-${citation.marker}`}
                className={cn(
                  "flex gap-3 p-3 rounded-md border text-xs transition-colors",
                  activeCitation === citation.marker
                    ? "border-blue-300 bg-blue-50"
                    : "border-[var(--border)] bg-[var(--muted)] hover:border-blue-200",
                )}
                onClick={() => setActiveCitation(activeCitation === citation.marker ? null : citation.marker)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) =>
                  e.key === "Enter" &&
                  setActiveCitation(activeCitation === citation.marker ? null : citation.marker)
                }
              >
                <span className="flex-shrink-0 w-5 h-5 rounded-full bg-blue-100 text-blue-700 font-bold text-[10px] flex items-center justify-center">
                  {citation.marker}
                </span>
                <div className="space-y-1 min-w-0">
                  <p className="font-medium text-gray-800 leading-snug">{citation.claim}</p>
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span
                      className={cn(
                        "px-1.5 py-0.5 rounded text-[10px] font-medium",
                        SOURCE_TYPE_COLORS[citation.source_type] ?? "bg-gray-100 text-gray-700",
                      )}
                    >
                      {citation.source_type}
                    </span>
                    {citation.section_title && (
                      <span className="text-[var(--muted-foreground)]">{citation.section_title}</span>
                    )}
                  </div>
                  {citation.source_text && (
                    <p className="text-gray-600 italic leading-relaxed">{citation.source_text}</p>
                  )}
                </div>
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}
