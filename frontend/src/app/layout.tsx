import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";

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
      "Normalizes fragmented clinical data from Mako, Velys, and ROSA robotic systems into structured prior auth submissions. Built by an ex-J&J/Velys engineer.",
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
    <html lang="en">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
