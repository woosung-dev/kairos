import type { NextConfig } from "next";
import { withSentryConfig } from "@sentry/nextjs";

// BUG-S27d-4 fix (Sprint 27d opus follow-up): clickjacking / MIME sniffing / referer leak 차단.
// CSP 는 의도적 SKIP — Clerk/R2/Next domain 정리 후 strict-dynamic 도입 (BL-S27e-3).
const securityHeaders = [
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  {
    key: "Permissions-Policy",
    value: "camera=(), microphone=(self), geolocation=()",
  },
];

const nextConfig: NextConfig = {
  async headers() {
    return [
      {
        source: "/:path*",
        headers: securityHeaders,
      },
    ];
  },
};

export default withSentryConfig(nextConfig, {
  silent: true,
  org: process.env.SENTRY_ORG,
  project: process.env.SENTRY_PROJECT,
});
