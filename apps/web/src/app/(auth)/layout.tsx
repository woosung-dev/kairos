// (auth) 라우트 레이아웃 — Provider 는 root layout 이 전역 제공(ISSUE-008).
// P1 fix (2026-06-01): ThemeProvider/QueryProvider/Toaster 이중 중첩 제거.
// query-client 의 useState(new QueryClient) 가 인스턴스마다 독립 → 캐시 분리/Toaster 중복 방지.
export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
