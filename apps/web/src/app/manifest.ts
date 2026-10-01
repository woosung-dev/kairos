import type { MetadataRoute } from "next";

// REQ-001 Web App Manifest → `/manifest.webmanifest` (docs/requirements/pwa.md §4.1).
// ★비로그인으로 읽혀야 한다 — 셀프호스팅에선 manifest 요청에 쿠키가 실리지 않는다
//   (pwa.md C-2). proxy.ts matcher 가 이 경로를 제외한다.
// 색은 앱 기본 테마(dark)의 배경 토큰 하나로 고정한다 (pwa.md C-10).
const BRAND_BACKGROUND = "#0A0A0B";

export default function manifest(): MetadataRoute.Manifest {
  return {
    // start_url 을 나중에 바꿔도 설치 앱 정체성이 유지되게 명시한다.
    id: "/",
    name: "Kairos",
    short_name: "Kairos",
    description: "회의, 노트, 자료가 쌓일수록 조직이 똑똑해집니다",
    // `/` 는 세션이 있으면 서버에서 /dashboard 로 다시 보낸다 — 왕복 1회를 줄인다 (pwa.md C-12).
    start_url: "/dashboard",
    scope: "/",
    display: "standalone",
    background_color: BRAND_BACKGROUND,
    theme_color: BRAND_BACKGROUND,
    lang: "ko",
    dir: "ltr",
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      {
        src: "/icons/icon-maskable-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "maskable",
      },
    ],
  };
}
