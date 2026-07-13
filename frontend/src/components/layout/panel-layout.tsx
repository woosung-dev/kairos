"use client";

import { useEffect, useCallback } from "react";
import dynamic from "next/dynamic";
import { useAuth } from "@clerk/nextjs";
import { useUIStore } from "@/store/ui";
import { useSourceViewerStore } from "@/features/sources/store";
import { useBreakpoint } from "@/hooks/use-media-query";
import { Sidebar } from "./sidebar";
import { Header } from "./header";
import { BottomNav } from "./bottom-nav";
import { Skeleton } from "@/components/ui/skeleton";

// 번들 분리 (PR-3 c1): RagPanel(react-markdown+remark-gfm)/CmdK/SourceViewer 를
// next/dynamic 으로 lazy-load — (app) 공용 청크에서 무거운 마크다운 파서를 이탈시킨다.
// 세 컴포넌트 모두 panel-layout 이 유일한 importer 이므로 여기 한 곳 전환으로 충분.
function PanelSkeleton() {
  return (
    <div className="flex flex-col gap-3 p-4">
      <Skeleton className="h-8 w-full" />
      <Skeleton className="h-4 w-3/4" />
      <Skeleton className="h-4 w-2/3" />
      <Skeleton className="h-32 w-full" />
    </div>
  );
}

const RagPanel = dynamic(
  () => import("./rag-panel").then((m) => m.RagPanel),
  { ssr: false, loading: () => <PanelSkeleton /> },
);
const CmdK = dynamic(() => import("./cmd-k").then((m) => m.CmdK), {
  ssr: false,
});
const SourceViewer = dynamic(
  () =>
    import("@/features/sources/components/source-viewer").then(
      (m) => m.SourceViewer,
    ),
  { ssr: false, loading: () => <PanelSkeleton /> },
);
import { useSyncWorkspaceRole } from "@/features/members/hooks";
import { useWorkspaces } from "@/features/workspaces/hooks";
import { useWorkspaceStore } from "@/features/workspaces/store";

export function PanelLayout({ children }: { children: React.ReactNode }) {
  const { isMobile, isCompact } = useBreakpoint();
  const { userId } = useAuth();
  const activeWorkspaceId = useWorkspaceStore((s) => s.activeWorkspaceId);
  const ensureOwner = useWorkspaceStore((s) => s.ensureOwner);
  const setActiveWorkspaceId = useWorkspaceStore((s) => s.setActiveWorkspaceId);
  const { data: workspaces } = useWorkspaces();

  // 계정 소유자 가드 (BL-S27c-12): 다른 user 로 전환되면 이전 user 의
  // activeWorkspaceId 를 즉시 초기화해 cross-tenant 403 을 막는다. user id 만
  // 비교하므로 워크스페이스 목록 로딩/생성 타이밍과 무관(race-free).
  useEffect(() => {
    if (userId) ensureOwner(userId);
  }, [userId, ensureOwner]);

  // activeWorkspaceId 가 비어있으면(초기/소유자 가드 직후) 첫 워크스페이스로 self-heal.
  // 비어있을 때만 채우므로 워크스페이스 생성/전환으로 막 설정된 wid 를 덮어쓰지 않는다.
  useEffect(() => {
    if (workspaces?.length && !activeWorkspaceId) {
      setActiveWorkspaceId(workspaces[0].id);
    }
  }, [workspaces, activeWorkspaceId, setActiveWorkspaceId]);

  // 워크스페이스 변경 시 역할 동기화
  useSyncWorkspaceRole(activeWorkspaceId ?? undefined);
  // Sprint 29 R3 (ui-store): selector 별 구독 — 이전 전체 구독은 무관한 UI state 변경
  // (cmdK open 등)에도 layout 골격 전체를 re-render 했다.
  const sidebarOpen = useUIStore((s) => s.sidebarOpen);
  const ragOverlayOpen = useUIStore((s) => s.ragOverlayOpen);
  const toggleRagOverlay = useUIStore((s) => s.toggleRagOverlay);
  const setSidebarCollapsed = useUIStore((s) => s.setSidebarCollapsed);
  const setIsMobile = useUIStore((s) => s.setIsMobile);
  const {
    source: sourceViewerSource,
    highlights: sourceViewerHighlights,
    close: closeSourceViewer,
  } = useSourceViewerStore();

  // breakpoint 변경 시 Zustand 동기화
  useEffect(() => {
    setIsMobile(isMobile);
    setSidebarCollapsed(isCompact);
  }, [isMobile, isCompact, setIsMobile, setSidebarCollapsed]);

  // ESC 키로 RAG 오버레이 닫기
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape" && ragOverlayOpen) {
        toggleRagOverlay();
      }
    },
    [ragOverlayOpen, toggleRagOverlay],
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  return (
    <div
      className="flex h-screen overflow-hidden"
      style={{ background: "var(--background)" }}
    >
      {/* 좌측 사이드바: 모바일 숨김, compact면 아이콘 모드 */}
      {!isMobile && sidebarOpen && <Sidebar collapsed={isCompact} />}

      {/* 중앙 콘텐츠 (넓은 메인) — F-2C fix (Sprint 25 polish v2, codex 2차 P3):
          skip-link 타깃. layout.tsx 의 '본문으로 건너뛰기' 가 #main-content 로
          jump → (app) 라우트 (dashboard/inbox/search/settings 등) 모두 본
          panel-layout 공유 → 단일 위치 fix 로 전체 (app) 라우트 커버. */}
      <main id="main-content" className="flex-1 flex flex-col overflow-hidden">
        <Header />
        <div
          className="flex-1 overflow-y-auto"
          style={{ paddingBottom: isMobile ? "var(--bottom-nav-height)" : "0" }}
        >
          {children}
        </div>
      </main>

      {/* RAG 오버레이: 우측에서 슬라이드 인 */}
      {ragOverlayOpen && (
        <>
          {/* 반투명 백드롭 */}
          <div
            className="fixed inset-0 z-30"
            style={{ background: "var(--backdrop-color)" }}
            onClick={toggleRagOverlay}
          />
          {/* 오버레이 패널 */}
          <div
            className="fixed right-0 top-0 h-full z-40 flex flex-col shadow-xl"
            style={{
              // BL-F5: <380px 뷰포트에서 고정 380px 패널이 가로 overflow → 뷰포트 폭으로 cap.
              width: "var(--rag-overlay-width)",
              maxWidth: "100%",
              background: "var(--surface)",
              borderLeft: "1px solid var(--border-subtle)",
            }}
          >
            {/* 오버레이 헤더 (닫기 버튼) */}
            <div
              className="flex items-center justify-between px-4 py-3 border-b shrink-0"
              style={{ borderColor: "var(--border-subtle)" }}
            >
              <span
                className="text-sm font-semibold"
                style={{
                  fontFamily: "var(--font-display)",
                  color: "var(--text-primary)",
                }}
              >
                지식 검색
              </span>
              <button
                onClick={toggleRagOverlay}
                className="p-1 rounded transition-colors hover:opacity-80"
                style={{ color: "var(--text-muted)" }}
                aria-label="AI 검색 패널 닫기"
              >
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
                  <path d="M1 1l12 12M13 1L1 13" />
                </svg>
              </button>
            </div>
            {/* RagPanel 재사용 (헤더 중복되나, RagPanel 내부 헤더는 필터/초기화 역할) */}
            <div className="flex-1 overflow-hidden">
              <RagPanel />
            </div>
          </div>
        </>
      )}

      {/* 소스 뷰어 모달 */}
      {sourceViewerSource && (
        <>
          <div
            className="fixed inset-0 z-50"
            style={{ background: "var(--backdrop-color)" }}
            onClick={closeSourceViewer}
          />
          <div
            className="fixed right-0 top-0 h-full z-50 flex flex-col shadow-xl"
            style={{
              width: isMobile ? "100%" : "var(--rag-overlay-width)",
              background: "var(--background)",
              borderLeft: isMobile ? "none" : "1px solid var(--border-subtle)",
            }}
          >
            <SourceViewer
              source={sourceViewerSource}
              highlightChunks={sourceViewerHighlights}
              onClose={closeSourceViewer}
            />
          </div>
        </>
      )}

      {/* Cmd+K 모달 */}
      <CmdK />

      {/* 모바일 하단 네비게이�� */}
      {isMobile && <BottomNav />}
    </div>
  );
}
