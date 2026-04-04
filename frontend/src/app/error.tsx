"use client";

import Link from "next/link";
import Image from "next/image";

export default function Error({ reset }: { error: Error; reset: () => void }) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--background)]">
      <div className="text-center space-y-4">
        <div className="flex items-center justify-center gap-2 mb-8">
          <Image src="/logo-globe.webp" alt="CortaLoom logo" width={32} height={32} />
          <span className="text-lg font-bold">CortaLoom</span>
        </div>
        <h1 className="text-4xl font-bold">Something went wrong</h1>
        <p className="text-[var(--muted-foreground)]">An unexpected error occurred. Please try again.</p>
        <div className="flex items-center justify-center gap-3 pt-2">
          <button
            onClick={reset}
            className="px-6 py-2.5 bg-[var(--primary)] text-[var(--primary-foreground)] rounded-lg font-semibold text-sm hover:opacity-90"
          >
            Try Again
          </button>
          <Link
            href="/"
            className="px-6 py-2.5 border border-[var(--border)] rounded-lg font-semibold text-sm hover:bg-[var(--muted)]"
          >
            Back to Home
          </Link>
        </div>
      </div>
    </div>
  );
}
