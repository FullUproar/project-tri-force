import Link from "next/link";
import Image from "next/image";

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-[var(--background)]">
      <header className="border-b border-[var(--border)] px-6 py-4">
        <div className="max-w-3xl mx-auto flex items-center gap-2">
          <Link href="/" className="flex items-center gap-2">
            <Image src="/logo-globe.webp" alt="CortaLoom logo" width={32} height={32} />
            <span className="text-lg font-bold">CortaLoom</span>
          </Link>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-6 py-12 space-y-8">
        <div>
          <h1 className="text-3xl font-bold mb-2">Privacy Policy</h1>
          <p className="text-sm text-[var(--muted-foreground)]">
            This policy is effective as of April 3, 2026. Contact legal@cortaloom.ai for questions.
          </p>
          <p className="text-xs text-[var(--muted-foreground)] mt-1">Last updated: April 3, 2026</p>
        </div>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">1. Data Collection</h2>
          <p className="text-sm text-[var(--muted-foreground)] leading-relaxed">
            CortaLoom collects information you provide directly, including account registration details
            (name, email, organization), clinical documents uploaded for processing, and usage data
            such as feature interactions and session duration. We do not collect data from third-party
            sources or use tracking cookies.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">2. Use of Data</h2>
          <p className="text-sm text-[var(--muted-foreground)] leading-relaxed">
            We use collected data to provide and improve the CortaLoom service, including AI-powered
            clinical data extraction and narrative generation. Account information is used for
            authentication, billing, and customer support. Aggregated, de-identified usage data may
            be used to improve our AI models and service quality.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">3. Data Sharing</h2>
          <p className="text-sm text-[var(--muted-foreground)] leading-relaxed">
            CortaLoom does not sell your data. We share information only with service providers
            necessary to operate the platform (cloud hosting, authentication, payment processing),
            and only under strict contractual obligations. We may disclose data if required by law
            or to protect the rights and safety of our users.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">4. HIPAA Compliance</h2>
          <p className="text-sm text-[var(--muted-foreground)] leading-relaxed">
            CortaLoom is designed to be HIPAA compliant. All Protected Health Information (PHI) is
            encrypted at rest and in transit. PHI is automatically scrubbed before AI processing.
            We maintain Business Associate Agreements (BAAs) with all subprocessors that handle PHI.
            Audit logs are maintained for all access to PHI. We conduct regular security assessments
            and maintain administrative, physical, and technical safeguards as required by the HIPAA
            Security Rule.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">5. Data Retention</h2>
          <p className="text-sm text-[var(--muted-foreground)] leading-relaxed">
            Clinical documents and extracted data are retained for the duration of your subscription
            and for a reasonable period thereafter to comply with legal obligations. You may request
            deletion of your data at any time by contacting us.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">6. Contact</h2>
          <p className="text-sm text-[var(--muted-foreground)] leading-relaxed">
            For privacy-related inquiries, contact our team at{" "}
            <a href="mailto:legal@cortaloom.ai" className="underline hover:text-[var(--foreground)]">
              legal@cortaloom.ai
            </a>.
          </p>
        </section>

        <div className="pt-4">
          <Link
            href="/"
            className="text-sm text-[var(--muted-foreground)] hover:text-[var(--foreground)] underline"
          >
            Back to Home
          </Link>
        </div>
      </main>
    </div>
  );
}
