"use client";

import { useEffect } from "react";
import { useUIStore } from "@/store/ui";
import { useBreakpoint } from "@/hooks/use-media-query";
import { Sidebar } from "./sidebar";
import { RagPanel } from "./rag-panel";
import { Header } from "./header";
import { CmdK } from "./cmd-k";
import { BottomNav } from "./bottom-nav";

export function PanelLayout({ children }: { children: React.ReactNode }) {
  const { isMobile, isCompact, isDesktop } = useBreakpoint();
  const { sidebarOpen, ragPanelOpen, setSidebarCollapsed, setIsMobile } =
    useUIStore();

  // breakpoint 변경 시 Zustand 동기화
  useEffect(() => {
    setIsMobile(isMobile);
    setSidebarCollapsed(isCompact);
  }, [isMobile, isCompact, setIsMobile, setSidebarCollapsed]);

  return (
    <div
      className="flex h-screen overflow-hidden"
      style={{ background: "var(--background)" }}
    >
      {/* 좌측 사이드바: 모바일 숨김, compact면 아이콘 모드 */}
      {!isMobile && sidebarOpen && <Sidebar collapsed={isCompact} />}

      {/* 중앙 콘텐츠 */}
      <main className="flex-1 flex flex-col overflow-hidden">
        <Header />
        <div
          className="flex-1 overflow-y-auto"
          style={{ paddingBottom: isMobile ? "var(--bottom-nav-height)" : "0" }}
        >
          {children}
        </div>
      </main>

      {/* 우측 RAG 패널: 데스크톱은 인라인, Compact는 슬라이드 오버 */}
      {!isMobile && isDesktop && ragPanelOpen && <RagPanel />}
      {isCompact && ragPanelOpen && (
        <div
          className="fixed right-0 top-0 h-full z-40 shadow-xl"
          style={{
            width: "var(--rag-panel-width)",
            background: "var(--surface)",
          }}
        >
          <RagPanel />
        </div>
      )}

      {/* Cmd+K 모달 */}
      <CmdK />

      {/* 모바일 하단 네비게이션 */}
      {isMobile && <BottomNav />}
    </div>
  );
}
