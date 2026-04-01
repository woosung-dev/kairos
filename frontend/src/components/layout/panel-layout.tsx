"use client";

import { useUIStore } from "@/store/ui";
import { Sidebar } from "./sidebar";
import { RagPanel } from "./rag-panel";
import { Header } from "./header";
import { CmdK } from "./cmd-k";

export function PanelLayout({ children }: { children: React.ReactNode }) {
  const { sidebarOpen, ragPanelOpen } = useUIStore();

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: "var(--background)" }}>
      {/* 좌측 사이드바 */}
      {sidebarOpen && <Sidebar />}

      {/* 중앙 콘텐츠 */}
      <main className="flex-1 flex flex-col overflow-hidden">
        <Header />
        <div className="flex-1 overflow-y-auto">
          {children}
        </div>
      </main>

      {/* 우측 RAG 패널 */}
      {ragPanelOpen && <RagPanel />}

      {/* Cmd+K 모달 */}
      <CmdK />
    </div>
  );
}
