import "@/lib/sentry";
import { ClerkProvider } from "@clerk/nextjs";
import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";
import { CookieConsent } from "@/components/cookie-consent";

export const metadata: Metadata = {
  title: "CortaLoom | ASC Prior Auth Agent",
  description:
    "AI-powered clinical data extraction and prior authorization for orthopaedic ambulatory surgery centers. Upload surgeon notes, robotic reports, or DICOM imaging — get a payer-ready narrative in seconds.",
  metadataBase: new URL("https://cortaloom.ai"),
  icons: {
    icon: "/favicon.webp",
  },
  openGraph: {
    title: "CortaLoom — AI Prior Authorization for Ortho ASCs",
    description:
      "Normalizes fragmented clinical data from Mako, Velys, and ROSA robotic systems into structured prior auth submissions. Built by orthopaedic industry engineers.",
    url: "https://cortaloom.ai",
    siteName: "CortaLoom",
    type: "website",
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 400,
        alt: "CortaLoom.AI — Clinical Data Middleware",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "CortaLoom — AI Prior Authorization for Ortho ASCs",
    description:
      "Upload clinical docs, get payer-ready narratives. AI middleware for orthopaedic surgery centers.",
    images: ["/og-image.png"],
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <ClerkProvider>
      <html lang="en">
        <body>
          <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:px-4 focus:py-2 focus:bg-[var(--primary)] focus:text-[var(--primary-foreground)] focus:rounded-lg">
            Skip to content
          </a>
          <Providers>{children}</Providers>
          <CookieConsent />
        </body>
      </html>
    </ClerkProvider>
  );
}
