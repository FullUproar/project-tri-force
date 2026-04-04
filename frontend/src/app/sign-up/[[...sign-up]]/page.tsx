import { SignUp } from "@clerk/nextjs";
import Image from "next/image";

export default function SignUpPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--background)]">
      <div className="text-center space-y-6">
        <div className="flex items-center justify-center gap-3">
          <Image src="/logo-globe.webp" alt="CortaLoom logo" width={40} height={40} />
          <h1 className="text-2xl font-bold">CortaLoom</h1>
        </div>
        <p className="text-sm text-[var(--muted-foreground)]">
          Create your ASC account
        </p>
        <SignUp />
      </div>
    </div>
  );
}
