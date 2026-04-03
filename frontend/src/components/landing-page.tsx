"use client";

import Link from "next/link";
import { Upload, Sparkles, FileDown, Shield, Clock, BarChart3, CheckCircle2 } from "lucide-react";

const FEATURES = [
  {
    icon: Upload,
    title: "Upload Any Clinical Document",
    description: "Drag and drop surgeon notes, robotic reports (Mako, Velys, ROSA), DICOM imaging, or PDFs. We handle the parsing.",
  },
  {
    icon: Sparkles,
    title: "AI Extracts What Payers Need",
    description: "ICD-10 codes, failed conservative treatments, implant details, and clinical justification — extracted in seconds, not hours.",
  },
  {
    icon: FileDown,
    title: "Generate Payer-Ready Narratives",
    description: "One click generates a professional prior authorization letter. Download as PDF or copy to your payer portal.",
  },
  {
    icon: Shield,
    title: "HIPAA Compliant by Design",
    description: "PHI is automatically scrubbed before AI processing. BAA-ready. Audit logging. Encryption at rest and in transit.",
  },
  {
    icon: Clock,
    title: "45 Minutes → 45 Seconds",
    description: "The average prior auth takes 45 minutes of manual work. CortaLoom does it in under a minute.",
  },
  {
    icon: BarChart3,
    title: "Track What Gets Approved",
    description: "Outcome tracking builds payer intelligence over time. Know which diagnosis-implant combos get approved, and which don't.",
  },
];

const TIERS = [
  { name: "Starter", price: 149, extractions: 50, description: "Small, single-specialty ASC" },
  { name: "Professional", price: 299, extractions: 150, description: "2-4 OR multi-specialty ASC", popular: true },
  { name: "Enterprise", price: 499, extractions: 350, description: "High-volume facility" },
];

export function LandingPage() {
  return (
    <div className="min-h-screen bg-[var(--background)]">
      {/* Nav */}
      <header className="border-b border-[var(--border)] px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <img src="/logo-globe.webp" alt="CortaLoom" className="w-8 h-8" />
            <span className="text-lg font-bold">CortaLoom</span>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/sign-in" className="text-sm text-[var(--muted-foreground)] hover:text-[var(--foreground)]">
              Sign in
            </Link>
            <Link
              href="/sign-up"
              className="px-4 py-2 bg-[var(--primary)] text-[var(--primary-foreground)] rounded-lg text-sm font-semibold hover:opacity-90"
            >
              Start Free Trial
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="px-6 py-20">
        <div className="max-w-4xl mx-auto text-center space-y-6">
          <h1 className="text-4xl md:text-5xl font-bold leading-tight">
            AI Prior Authorization
            <br />
            <span
              style={{
                background: "linear-gradient(to right, #2563eb, #4f46e5)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
              }}
            >
              for Orthopaedic ASCs
            </span>
          </h1>
          <p className="text-lg text-[var(--muted-foreground)] max-w-2xl mx-auto">
            Upload a surgeon's note. Get a payer-ready narrative in seconds.
            CortaLoom extracts ICD-10 codes, failed treatments, and implant details
            from clinical documents — so your team stops spending hours on prior auth.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
            <Link
              href="/sign-up"
              className="w-full sm:w-auto px-8 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg font-semibold text-center hover:from-blue-700 hover:to-indigo-700"
            >
              Start Free Trial
            </Link>
            <Link
              href="/sign-in"
              className="w-full sm:w-auto px-8 py-3 border border-[var(--border)] rounded-lg font-semibold text-center hover:bg-[var(--muted)]"
            >
              Sign In
            </Link>
          </div>
          <p className="text-xs text-[var(--muted-foreground)]">
            No credit card required. HIPAA compliant. Built by orthopaedic industry engineers.
          </p>
        </div>
      </section>

      {/* Features */}
      <section className="px-6 py-16 bg-[var(--muted)]">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-2xl font-bold text-center mb-12">
            Everything your ASC needs for prior auth
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {FEATURES.map((feature) => (
              <div key={feature.title} className="space-y-3">
                <feature.icon className="w-8 h-8 text-blue-600" />
                <h3 className="font-bold">{feature.title}</h3>
                <p className="text-sm text-[var(--muted-foreground)] leading-relaxed">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section className="px-6 py-16">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-2xl font-bold text-center mb-2">Simple, transparent pricing</h2>
          <p className="text-center text-sm text-[var(--muted-foreground)] mb-12">
            All plans include HIPAA compliance, AI extraction, narrative generation, and analytics.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {TIERS.map((tier) => (
              <div
                key={tier.name}
                className={`p-6 border rounded-xl space-y-4 ${
                  tier.popular ? "border-blue-400 ring-2 ring-blue-200 relative" : "border-[var(--border)]"
                }`}
              >
                {tier.popular && (
                  <span className="absolute -top-3 left-4 px-2 py-0.5 bg-blue-600 text-white text-xs font-bold rounded">
                    Most Popular
                  </span>
                )}
                <div>
                  <h3 className="font-bold text-lg">{tier.name}</h3>
                  <p className="text-xs text-[var(--muted-foreground)]">{tier.description}</p>
                </div>
                <div className="flex items-baseline gap-1">
                  <span className="text-3xl font-bold">${tier.price}</span>
                  <span className="text-sm text-[var(--muted-foreground)]">/mo</span>
                </div>
                <ul className="space-y-2 text-sm">
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-green-500" />
                    {tier.extractions} extractions/month
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-green-500" />
                    + $2.50/extraction overage
                  </li>
                </ul>
                <Link
                  href="/sign-up"
                  className={`block w-full py-2.5 rounded-lg font-semibold text-sm text-center ${
                    tier.popular
                      ? "bg-blue-600 text-white hover:bg-blue-700"
                      : "bg-[var(--primary)] text-[var(--primary-foreground)] hover:opacity-90"
                  }`}
                >
                  Start Free Trial
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="px-6 py-16 bg-gradient-to-r from-blue-600 to-indigo-600">
        <div className="max-w-3xl mx-auto text-center space-y-6">
          <h2 className="text-2xl md:text-3xl font-bold text-white">
            Stop losing hours to prior auth paperwork
          </h2>
          <p className="text-blue-100">
            Join the ASCs using AI to get approvals faster and reduce denials.
          </p>
          <Link
            href="/sign-up"
            className="inline-block px-8 py-3 bg-white text-blue-700 rounded-lg font-semibold hover:bg-blue-50"
          >
            Start Your Free Trial
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="px-6 py-8 border-t border-[var(--border)]">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <img src="/logo-globe.webp" alt="CortaLoom" className="w-6 h-6" />
            <span className="text-sm text-[var(--muted-foreground)]">
              CortaLoom AI, Inc.
            </span>
          </div>
          <p className="text-xs text-[var(--muted-foreground)]">
            HIPAA Compliant | SOC 2 Type II (planned) | Built in Indiana
          </p>
        </div>
      </footer>
    </div>
  );
}
