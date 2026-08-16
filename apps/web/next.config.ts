import type { NextConfig } from "next";

// BUG-S27d-4 fix (Sprint 27d opus follow-up): clickjacking / MIME sniffing / referer leak 차단.
// CSP 는 아직 SKIP (BL-S27e-3). ADR-031 로 Clerk 도메인이, ADR-028 로 Sentry 가 사라져
// 정리 대상 외부 도메인은 폰트(fontshare/jsdelivr)와 R2 정도로 줄었다 — 진입 장벽이 낮아진 상태.
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
