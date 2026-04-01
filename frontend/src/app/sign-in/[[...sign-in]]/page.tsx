import { SignIn } from "@clerk/nextjs";

export default function SignInPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--background)]">
      <div className="text-center space-y-6">
        <div className="flex items-center justify-center gap-3">
          <img src="/logo-globe.webp" alt="CortaLoom" className="w-10 h-10" />
          <h1 className="text-2xl font-bold">CortaLoom</h1>
        </div>
        <p className="text-sm text-[var(--muted-foreground)]">
          AI Prior Authorization for Orthopaedic ASCs
        </p>
        <SignIn />
      </div>
    </div>
  );
}
