import type { Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import { koKR } from "@clerk/localizations";
import { ThemeProvider } from "@/components/layout/theme-provider";
import { QueryProvider } from "@/lib/query-client";
import { Toaster } from "@/components/ui/sonner";
import "./globals.css";

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
    <ClerkProvider localization={koKR}>
      <html lang="ko" suppressHydrationWarning>
        <head>
          <link rel="preconnect" href="https://fonts.googleapis.com" />
          <link
            rel="preconnect"
            href="https://fonts.gstatic.com"
            crossOrigin="anonymous"
          />
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
            href="https://fonts.googleapis.com/css2?family=Geist+Mono:wght@400;500&display=swap"
            rel="stylesheet"
          />
          <link
            href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/variable/pretendardvariable-dynamic-subset.css"
            rel="stylesheet"
          />
        </head>
        <body>
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
    </ClerkProvider>
  );
}
