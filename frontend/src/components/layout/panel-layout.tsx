import { Header } from "./header";
import { Sidebar } from "./sidebar";
import { RAGPanel } from "./rag-panel";
import { MobileSidebar } from "./mobile-sidebar";

export function PanelLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden">
      {/* 좌측 사이드바 — 데스크톱 */}
      <div className="hidden lg:block">
        <Sidebar />
      </div>

      {/* 좌측 사이드바 — 모바일 (Sheet) */}
      <MobileSidebar />

      {/* 메인 영역 */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto">
          {children}
        </main>
      </div>

      {/* 우측 RAG 패널 */}
      <RAGPanel />
    </div>
  );
}
