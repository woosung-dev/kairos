"use client";

import { useEffect, useCallback } from "react";
import { useUIStore } from "@/store/ui";
import { useBreakpoint } from "@/hooks/use-media-query";
import { Sidebar } from "./sidebar";
import { RagPanel } from "./rag-panel";
import { Header } from "./header";
import { CmdK } from "./cmd-k";
import { BottomNav } from "./bottom-nav";
import { SourceViewer } from "@/features/sources/components/source-viewer";
import { useSyncWorkspaceRole } from "@/features/members/hooks";
import { useWorkspaceStore } from "@/features/workspaces/store";

export function PanelLayout({ children }: { children: React.ReactNode }) {
  const { isMobile, isCompact } = useBreakpoint();
  const activeWorkspaceId = useWorkspaceStore((s) => s.activeWorkspaceId);

  // 워크스페이스 변경 시 역할 동기화
  useSyncWorkspaceRole(activeWorkspaceId ?? undefined);
  const {
    sidebarOpen,
    ragOverlayOpen,
    toggleRagOverlay,
    setSidebarCollapsed,
    setIsMobile,
    sourceViewerSource,
    sourceViewerHighlights,
    closeSourceViewer,
  } = useUIStore();

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

      {/* 중앙 콘텐츠 (넓은 메인) */}
      <main className="flex-1 flex flex-col overflow-hidden">
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
              width: "var(--rag-overlay-width)",
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
