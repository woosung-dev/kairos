export default function LandingLayout({ children }: { children: React.ReactNode }) {
  // ThemeProvider 없이 data-theme="landing" wrapper로 직접 테마 고정
  // → next-themes hydration 간섭 없이 랜딩 테마 CSS 변수 적용
  return <div data-theme="landing">{children}</div>;
}
