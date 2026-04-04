import Link from "next/link";
import Image from "next/image";

export default function TermsPage() {
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
          <h1 className="text-3xl font-bold mb-2">Terms of Service</h1>
          <p className="text-sm text-[var(--muted-foreground)]">
            This policy is effective as of April 3, 2026. Contact legal@cortaloom.ai for questions.
          </p>
          <p className="text-xs text-[var(--muted-foreground)] mt-1">Last updated: April 3, 2026</p>
        </div>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">1. Acceptance of Terms</h2>
          <p className="text-sm text-[var(--muted-foreground)] leading-relaxed">
            By accessing or using CortaLoom, you agree to be bound by these Terms of Service. If you
            do not agree to these terms, you may not use the service. These terms apply to all users,
            including administrators, staff, and any other individuals accessing the platform on behalf
            of a healthcare organization.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">2. Service Description</h2>
          <p className="text-sm text-[var(--muted-foreground)] leading-relaxed">
            CortaLoom provides AI-powered clinical data extraction and prior authorization narrative
            generation for orthopaedic ambulatory surgery centers (ASCs). The service processes
            uploaded clinical documents to extract structured data including diagnosis codes,
            conservative treatments, implant details, and generates payer-ready narratives.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">3. Limitations of Service</h2>
          <p className="text-sm text-[var(--muted-foreground)] leading-relaxed">
            CortaLoom is a clinical data processing tool and does not provide medical advice.
            All AI-generated extractions and narratives should be reviewed by qualified clinical
            staff before submission to payers. CortaLoom does not guarantee prior authorization
            approval. The accuracy of extracted data depends on the quality and completeness of
            uploaded source documents.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">4. HIPAA and Compliance</h2>
          <p className="text-sm text-[var(--muted-foreground)] leading-relaxed">
            CortaLoom maintains HIPAA compliance for all Protected Health Information (PHI) processed
            through the platform. Customers must execute a Business Associate Agreement (BAA) with
            CortaLoom prior to uploading any PHI. You are responsible for ensuring that your use of
            the service complies with all applicable federal, state, and local healthcare regulations.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">5. Account Responsibilities</h2>
          <p className="text-sm text-[var(--muted-foreground)] leading-relaxed">
            You are responsible for maintaining the confidentiality of your account credentials and
            for all activity that occurs under your account. You must promptly notify CortaLoom of
            any unauthorized access to your account. Organizations are responsible for managing user
            access and ensuring only authorized personnel use the service.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">6. Termination</h2>
          <p className="text-sm text-[var(--muted-foreground)] leading-relaxed">
            Either party may terminate this agreement at any time. Upon termination, your access to
            the service will be revoked. CortaLoom will retain your data for a reasonable period to
            comply with legal obligations, after which it will be securely deleted. You may request
            an export of your data prior to termination.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">7. Contact</h2>
          <p className="text-sm text-[var(--muted-foreground)] leading-relaxed">
            For questions about these terms, contact{" "}
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
