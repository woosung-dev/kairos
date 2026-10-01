import type { Metadata, Viewport } from "next";
import { Geist_Mono } from "next/font/google";
import { ThemeProvider } from "@/components/layout/theme-provider";
import { ServiceWorkerRegistrar } from "@/components/layout/service-worker-registrar";
import { QueryProvider } from "@/lib/query-client";
import { Toaster } from "@/components/ui/sonner";
import "./globals.css";

// Sprint 28 PERF-10 — Geist Mono self-host (next/font/google).
// Satoshi (Fontshare) + Pretendard (jsdelivr) 는 next/font/google 미지원
// → 별도 sprint local woff2 다운로드 후 next/font/local (BL-S27e-D carry).
// 본 fix: Geist Mono 만 self-host → 외부 fonts.googleapis.com / fonts.gstatic.com
// preconnect 제거 가능 (LCP 부분 회복).
const geistMono = Geist_Mono({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-geist-mono",
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: "Kairos — 팀의 세컨드 브레인",
  description: "회의, 노트, 자료가 쌓일수록 조직이 똑똑해집니다",
  // PWA 설치형 셸 (docs/requirements/pwa.md §4.3). manifest <link> 는 app/manifest.ts 가 만든다.
  // statusBarStyle 은 default — black-translucent 는 웹뷰가 상태바 밑까지 올라가 헤더 상단
  // safe-area 처리가 추가로 필요하다 (BL-PWA-10).
  appleWebApp: { capable: true, title: "Kairos", statusBarStyle: "default" },
  // ★Next 아이콘 파일 컨벤션(app/apple-icon.png)을 쓰지 않는다 — href 가 확장자 없는 경로면
  //   proxy matcher 의 .png 제외에 걸리지 않아 로그인 리다이렉트될 수 있다 (pwa.md §4.2).
  icons: { apple: "/icons/apple-touch-icon.png" },
};

// themeColor 는 앱 기본 테마(dark) 배경 단일값 — OS media 배열은 앱 테마와 어긋난다 (pwa.md C-10).
// viewportFit=cover 여야 env(safe-area-inset-*) 가 0 이 아니다 (globals.css · bottom-nav).
export const viewport: Viewport = {
  themeColor: "#0A0A0B",
  viewportFit: "cover",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko" suppressHydrationWarning className={geistMono.variable}>
      <head>
        {/* Sprint 28 PERF-10 partial — Geist Mono 는 next/font/google 적용 (self-host).
            Satoshi + Pretendard 는 BL-S27e-D carry (next/font/local woff2 다운로드 필요). */}
        <link rel="preconnect" href="https://api.fontshare.com" />
        <link rel="preconnect" href="https://cdn.fontshare.com" crossOrigin="anonymous" />
        {/* BL-045 (Sprint 18): Satoshi 는 Indian Type Foundry/Fontshare 호스팅.
            Google Fonts 미배포 — 기존 URL 영구 pending → FOIT 위험.
            DESIGN.md §Typography 정합. */}
        <link
          href="https://api.fontshare.com/v2/css?f[]=satoshi@400,500,600,700&display=swap"
          rel="stylesheet"
        />
        <link
          href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/variable/pretendardvariable-dynamic-subset.css"
          rel="stylesheet"
        />
      </head>
      <body>
        {/* T-A11Y-1 (Sprint 25): skip-link — 키보드 사용자가 nav 를 건너뛰고
            main content 로 즉시 이동. focus 시에만 노출 (visual user UX 무영향). */}
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-[100] focus:rounded-lg focus:bg-foreground focus:px-4 focus:py-2 focus:text-sm focus:text-background focus:shadow-lg"
        >
          본문으로 건너뛰기
        </a>
        {/* ThemeProvider 는 root layout body 최상위에 위치해야 inline FOUC
            방지 script 가 React component tree 깊은 곳에서 렌더되어 발생하는
            "Encountered a script tag while rendering React component" 경고
            회피 가능 (next-themes 0.4 + Next.js 16 정합).
            QueryProvider 도 root 에 둬서 /invite 등 (app) 외부 라우트도
            React Query 사용 가능 (ISSUE-008 fix). */}
        <ThemeProvider>
          <QueryProvider>
            {children}
            <Toaster />
          </QueryProvider>
        </ThemeProvider>
        <ServiceWorkerRegistrar />
      </body>
    </html>
  );
}
