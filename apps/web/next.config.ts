import type { NextConfig } from "next";

// BUG-S27d-4 fix (Sprint 27d opus follow-up): clickjacking / MIME sniffing / referer leak 차단.
// CSP 는 의도적 SKIP — Clerk/R2/Next domain 정리 후 strict-dynamic 도입 (BL-S27e-3).
const securityHeaders = [
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  {
    key: "Permissions-Policy",
    value: "camera=(self), microphone=(self), geolocation=()",
  },
];

const nextConfig: NextConfig = {
  // ADR-028 OCI 셀프호스팅 — Vercel 이 대신하던 배포 산출물 생성을 직접 한다.
  // .next/standalone 에 server.js + 필요한 node_modules 만 담긴다 (Dockerfile runner 스테이지가 복사).
  output: "standalone",
  async headers() {
    return [
      {
        source: "/:path*",
        headers: securityHeaders,
      },
    ];
  },
};

export default nextConfig;
