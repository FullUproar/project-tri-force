import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: "*", allow: "/", disallow: ["/api/", "/admin", "/rep", "/billing", "/analytics", "/onboarding"] },
    sitemap: "https://cortaloom.ai/sitemap.xml",
  };
}
