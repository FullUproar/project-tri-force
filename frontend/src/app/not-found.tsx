import Link from "next/link";
import Image from "next/image";

export default function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--background)]">
      <div className="text-center space-y-4">
        <div className="flex items-center justify-center gap-2 mb-8">
          <Image src="/logo-globe.webp" alt="CortaLoom logo" width={32} height={32} />
          <span className="text-lg font-bold">CortaLoom</span>
        </div>
        <h1 className="text-6xl font-bold text-[var(--muted-foreground)]">404</h1>
        <p className="text-lg text-[var(--muted-foreground)]">Page not found</p>
        <Link
          href="/"
          className="inline-block px-6 py-2.5 bg-[var(--primary)] text-[var(--primary-foreground)] rounded-lg font-semibold text-sm hover:opacity-90"
        >
          Back to Home
        </Link>
      </div>
    </div>
  );
}
