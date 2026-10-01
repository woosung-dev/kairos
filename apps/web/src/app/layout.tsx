import type { Metadata } from "next";
import localFont from "next/font/local";
import { ThemeProvider } from "@/components/layout/theme-provider";
import { QueryProvider } from "@/lib/query-client";
import { Toaster } from "@/components/ui/sonner";
import "./globals.css";

// Geist Mono — 레포에 둔 woff2 를 next/font/local 로 self-host (2026-10-02).
// next/font/google 은 빌드 때 Google Fonts 를 내려받는데, CI frontend-build 에서
// 그 다운로드가 간헐 실패했다 (같은 커밋 재실행은 통과). 빌드가 네트워크에 기대지 않게 한다.
// 파일 = Google Fonts 가 400·500 에 같이 내주는 latin 서브셋 가변 폰트 (wght 축). 라이선스 OFL.txt.
// Satoshi (Fontshare) + Pretendard (jsdelivr) 는 아직 외부 CDN (BL-S27e-D carry).
const geistMono = localFont({
  src: "./fonts/GeistMono-latin-wght.woff2",
  display: "swap",
  variable: "--font-geist-mono",
  weight: "400 500",
});

export const metadata: Metadata = {
  title: "Kairos — 팀의 세컨드 브레인",
  description: "회의, 노트, 자료가 쌓일수록 조직이 똑똑해집니다",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko" suppressHydrationWarning className={geistMono.variable}>
      <head>
        {/* Sprint 28 PERF-10 partial — Geist Mono 는 next/font/local 로 self-host.
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
      </body>
    </html>
  );
}
