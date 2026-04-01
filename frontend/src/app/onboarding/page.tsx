"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { CheckCircle2, Circle, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface Step {
  id: string;
  title: string;
  description: string;
  completed: boolean;
  action?: () => void;
  actionLabel?: string;
}

export default function OnboardingPage() {
  const router = useRouter();
  const [steps, setSteps] = useState<Step[]>([
    {
      id: "baa",
      title: "Sign Business Associate Agreement",
      description:
        "HIPAA requires a BAA before any clinical data can be processed. Contact support@cortaloom.ai to execute your BAA.",
      completed: false,
      actionLabel: "Email Support",
      action: () => window.open("mailto:support@cortaloom.ai?subject=BAA%20Request%20-%20New%20ASC", "_blank"),
    },
    {
      id: "test-case",
      title: "Run a test case",
      description:
        "Try the platform with a sample clinical note. No real patient data needed — our demo uses synthetic data.",
      completed: false,
      actionLabel: "Go to Dashboard",
      action: () => router.push("/"),
    },
    {
      id: "upload",
      title: "Upload your first real case",
      description:
        "Upload a surgeon's clinical note, robotic report PDF, or DICOM file. PHI is automatically scrubbed before AI processing.",
      completed: false,
      actionLabel: "Go to Dashboard",
      action: () => router.push("/"),
    },
    {
      id: "narrative",
      title: "Generate your first payer narrative",
      description:
        "After extraction completes, click 'Generate Payer Submission Narrative' to create a prior auth letter. Download as PDF or copy to clipboard.",
      completed: false,
    },
  ]);

  // Check completion from localStorage (simple client-side tracking)
  useEffect(() => {
    const saved = localStorage.getItem("cortaloom-onboarding");
    if (saved) {
      const completed: string[] = JSON.parse(saved);
      setSteps((prev) =>
        prev.map((s) => ({ ...s, completed: completed.includes(s.id) }))
      );
    }
  }, []);

  const markComplete = (id: string) => {
    setSteps((prev) => {
      const updated = prev.map((s) => (s.id === id ? { ...s, completed: true } : s));
      const completedIds = updated.filter((s) => s.completed).map((s) => s.id);
      localStorage.setItem("cortaloom-onboarding", JSON.stringify(completedIds));
      return updated;
    });
  };

  const allComplete = steps.every((s) => s.completed);
  const completedCount = steps.filter((s) => s.completed).length;

  return (
    <div className="min-h-screen bg-[var(--background)]">
      <header className="border-b border-[var(--border)] px-6 py-4">
        <div className="max-w-3xl mx-auto flex items-center gap-3">
          <img src="/logo-globe.webp" alt="CortaLoom" className="w-9 h-9" />
          <div>
            <h1 className="text-xl font-bold">Welcome to CortaLoom</h1>
            <p className="text-xs text-[var(--muted-foreground)]">
              Get your ASC set up in 4 steps
            </p>
          </div>
        </div>
      </header>

      <main className="max-w-3xl mx-auto p-6 space-y-6">
        {/* Progress */}
        <div className="flex items-center justify-between p-4 bg-[var(--muted)] rounded-lg">
          <span className="text-sm font-medium">
            {completedCount} of {steps.length} steps complete
          </span>
          <div className="w-48 bg-[var(--border)] rounded-full h-2">
            <div
              className="h-2 rounded-full bg-[var(--primary)] transition-all"
              style={{ width: `${(completedCount / steps.length) * 100}%` }}
            />
          </div>
        </div>

        {/* Steps */}
        <div className="space-y-4">
          {steps.map((step, i) => (
            <div
              key={step.id}
              className={cn(
                "p-5 border rounded-lg transition-colors",
                step.completed
                  ? "border-[var(--success)] bg-green-50/50"
                  : "border-[var(--border)]"
              )}
            >
              <div className="flex items-start gap-4">
                <div className="mt-0.5">
                  {step.completed ? (
                    <CheckCircle2 className="w-6 h-6 text-[var(--success)]" />
                  ) : (
                    <Circle className="w-6 h-6 text-[var(--muted-foreground)]" />
                  )}
                </div>
                <div className="flex-1">
                  <h3 className={cn("font-semibold", step.completed && "line-through opacity-60")}>
                    Step {i + 1}: {step.title}
                  </h3>
                  <p className="text-sm text-[var(--muted-foreground)] mt-1">
                    {step.description}
                  </p>
                  {!step.completed && (
                    <div className="flex items-center gap-3 mt-3">
                      {step.action && (
                        <button
                          onClick={step.action}
                          className="flex items-center gap-1 px-3 py-1.5 text-sm font-medium bg-[var(--primary)] text-[var(--primary-foreground)] rounded-md hover:opacity-90"
                        >
                          {step.actionLabel} <ArrowRight className="w-3.5 h-3.5" />
                        </button>
                      )}
                      <button
                        onClick={() => markComplete(step.id)}
                        className="text-sm text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
                      >
                        Mark as done
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        {allComplete && (
          <div className="p-6 text-center bg-green-50 border border-green-200 rounded-lg">
            <h2 className="text-lg font-bold text-green-800">You're all set!</h2>
            <p className="text-sm text-green-700 mt-1">
              Your ASC is ready to use CortaLoom for prior authorization.
            </p>
            <button
              onClick={() => router.push("/")}
              className="mt-4 px-6 py-2 bg-[var(--primary)] text-[var(--primary-foreground)] rounded-md font-medium hover:opacity-90"
            >
              Go to Dashboard
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
