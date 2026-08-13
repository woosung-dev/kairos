// (app) 그룹 — QueryProvider + ThemeProvider + Toaster 는 root layout 에 위치.
// 본 layout 은 PanelLayout 만 wrap (사이드바 + 헤더 + 메인 컨테이너).
import { PanelLayout } from "@/components/layout/panel-layout";
import { FeedbackButton } from "@/features/feedback/components/feedback-button";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <PanelLayout>
      {children}
      {/* dogfooding 피드백 우하단 floating 버튼 (Sprint 28 Wave 1) */}
      <FeedbackButton />
    </PanelLayout>
  );
}
