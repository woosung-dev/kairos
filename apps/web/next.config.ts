import type { NextConfig } from "next";

// BUG-S27d-4 fix (Sprint 27d opus follow-up): clickjacking / MIME sniffing / referer leak 차단.

// ADR-026 D5 — Google Picker 도입에 필요한 CSP.
//
// 외부 origin 인벤토리 (2026-09-11 전수 grep):
//   폰트  api.fontshare.com(css) · cdn.fontshare.com(woff2) · cdn.jsdelivr.net(Pretendard)
//   Picker apis.google.com(loader) · accounts.google.com(GIS) · docs.google.com(iframe)
//   API   NEXT_PUBLIC_API_URL (빌드 인자 — R2 직접 업로드는 없다. 프록시 경유, BL-OCI-2)
//
// ★`'unsafe-inline'` 이 script-src 에 남아 있다 — Next 의 부트스트랩 인라인 스크립트와
//   ThemeProvider 의 FOUC 방지 스크립트가 nonce 없이는 죽는다. nonce + strict-dynamic
//   전환은 middleware 가 필요하며 BL-S27e-3 의 범위다. 여기서는 **Picker 가 요구하는
//   최소 지시문**만 연다.
const API_ORIGIN = (() => {
  try {
    return new URL(
      process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
    ).origin;
  } catch {
    return "http://localhost:8000";
  }
})();

const cspDirectives = [
  "default-src 'self'",
  // 'unsafe-eval' 은 dev 의 React Refresh 에 필요하다. production 빌드는 쓰지 않는다.
  `script-src 'self' 'unsafe-inline'${
    process.env.NODE_ENV === "production" ? "" : " 'unsafe-eval'"
  } https://apis.google.com https://accounts.google.com`,
  "style-src 'self' 'unsafe-inline' https://api.fontshare.com https://cdn.jsdelivr.net",
  "font-src 'self' data: https://cdn.fontshare.com https://cdn.jsdelivr.net",
  // Picker 썸네일은 여러 googleusercontent 서브도메인에서 온다 — 열거가 불가능하다.
  "img-src 'self' data: blob: https:",
  // 녹음 미리듣기는 blob: object URL 이다 (app/(app)/new/page.tsx).
  "media-src 'self' blob: data:",
  // ★Picker 는 googleapis.com 뿐 아니라 로더 호스트와 docs/content 서브도메인으로도
  //   XHR 을 낸다. frame-src 에만 넣고 connect-src 에서 빼면 enforcing 으로 올리는
  //   순간 파일 목록이 blocked 로 죽는다 — 이 CSP 가 존재하는 이유가 그 기능이다.
  `connect-src 'self' ${API_ORIGIN} https://www.googleapis.com https://accounts.google.com https://apis.google.com https://content.googleapis.com https://docs.google.com`,
  // GIS 토큰 팝업과 Picker 본체가 iframe 으로 뜬다.
  "frame-src 'self' https://accounts.google.com https://docs.google.com https://content.googleapis.com",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
].join("; ");

const securityHeaders = [
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  {
    key: "Permissions-Policy",
    value: "camera=(self), microphone=(self), geolocation=()",
  },
  // ★Report-Only 로 시작한다 — 의도적이다.
  //
  //   이 정책은 정적 grep 으로 만들었고 **브라우저에서 검증되지 않았다.** 곧바로
  //   enforcing 으로 켰다가 directive 가 하나라도 모자라면 앱이 조용히 깨진다.
  //   부팅 차단형 validator 로 prod 를 전면 다운시킨 ADR-024 사고와 같은 실패
  //   모드다.
  //
  //   전환 절차: 배포 후 주요 경로(로그인 · /new 녹음 · RAG 검색 · 설정>연동에서
  //   Picker 열기)를 돌며 콘솔의 "Content-Security-Policy" 위반 0건을 확인한 뒤
  //   이 key 를 "Content-Security-Policy" 로 바꾼다. 추적: BL-S27e-3.
  { key: "Content-Security-Policy-Report-Only", value: cspDirectives },
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
