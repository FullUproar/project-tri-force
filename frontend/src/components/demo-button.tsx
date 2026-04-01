"use client";

import { useState } from "react";
import { Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

const SAMPLE_NOTE = `ORTHOPAEDIC CONSULTATION NOTE

Patient presents with severe right knee pain consistent with end-stage osteoarthritis.
Weight-bearing AP and lateral radiographs demonstrate Kellgren-Lawrence Grade IV changes
with complete loss of medial joint space, subchondral sclerosis, and large osteophyte
formation. 12-degree varus malalignment.

DIAGNOSIS: Primary osteoarthritis, right knee (ICD-10: M17.11)

CONSERVATIVE TREATMENT HISTORY:
- NSAIDs (Meloxicam 15mg daily) x 8 months - inadequate pain relief
- Physical therapy (3x/week for 8 weeks) - completed without significant improvement
- Cortisone injection (40mg triamcinolone acetonide) - temporary relief lasting 3 weeks
- Hyaluronic acid viscosupplementation (Synvisc-One) - no meaningful benefit
- Unloader brace x 6 months - minimal benefit

RECOMMENDATION:
Given failure of all reasonable conservative measures and severity of radiographic
findings with significant functional limitation, recommend right total knee arthroplasty
using the Stryker Triathlon Total Knee System with Mako robotic-assisted surgical technique.

Mako robotic assistance is indicated to optimize implant positioning and achieve precise
ligament balance, particularly important given the significant varus deformity.`;

import { uploadClinicalNoteText } from "@/lib/api";

interface DemoButtonProps {
  onJobCreated: (jobId: string) => void;
}

export function DemoButton({ onJobCreated }: DemoButtonProps) {
  const [loading, setLoading] = useState(false);

  const handleDemo = async () => {
    setLoading(true);
    try {
      const data = await uploadClinicalNoteText(SAMPLE_NOTE);
      onJobCreated(data.job_id);
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      onClick={handleDemo}
      disabled={loading}
      className={cn(
        "flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors",
        "bg-gradient-to-r from-blue-600 to-indigo-600 text-white",
        "hover:from-blue-700 hover:to-indigo-700",
        "disabled:opacity-50 disabled:cursor-not-allowed"
      )}
    >
      <Sparkles className={cn("w-4 h-4", loading && "animate-pulse")} />
      {loading ? "Processing..." : "Try Demo"}
    </button>
  );
}
