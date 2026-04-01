"use client";

import { useState } from "react";
import { Copy, Check, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";
import type { NarrativeResponse } from "@/lib/api";

interface NarrativePanelProps {
  narrative: NarrativeResponse | null;
  onRegenerate: () => void;
  isRegenerating: boolean;
}

export function NarrativePanel({ narrative, onRegenerate, isRegenerating }: NarrativePanelProps) {
  const [copied, setCopied] = useState(false);

  if (!narrative) return null;

  const handleCopy = async () => {
    await navigator.clipboard.writeText(narrative.narrative_text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
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

      <div className="prose prose-sm max-w-none text-sm leading-relaxed whitespace-pre-wrap bg-[var(--muted)] p-4 rounded-md">
        {narrative.narrative_text}
      </div>
    </div>
  );
}
