"use client";

import { EmptyState } from "@/components/empty-state";
import { useUIStore } from "@/store/ui";

export default function RagHomePage() {
  const { toggleCmdK } = useUIStore();

  return (
    <div className="flex flex-col items-center px-4 py-12">
      {/* 검색 바 */}
      <div className="w-full max-w-2xl mb-12">
        <h1
          className="text-2xl font-bold mb-6 text-center"
          style={{ fontFamily: "var(--font-display)", color: "var(--text-primary)" }}
        >
          무엇이든 질문하세요
        </h1>
        <button
          onClick={toggleCmdK}
          className="w-full flex items-center justify-between px-4 py-3 rounded border text-sm transition-colors"
          style={{
            background: "var(--surface)",
            borderColor: "var(--border)",
            color: "var(--text-muted)",
            borderRadius: "var(--radius-md)",
          }}
        >
          <span>검색하거나 질문 입력...</span>
          <kbd
            className="px-2 py-0.5 rounded text-[10px]"
            style={{
              background: "var(--surface-active)",
              borderRadius: "var(--radius-sm)",
              fontFamily: "var(--font-mono)",
            }}
          >
            ⌘K
          </kbd>
        </button>
      </div>

      {/* 최근 질문 */}
      <div className="w-full max-w-2xl mb-12">
        <h2
          className="text-sm font-semibold mb-4 uppercase tracking-wider"
          style={{ color: "var(--text-muted)", fontFamily: "var(--font-display)" }}
        >
          최근 질문
        </h2>
        <EmptyState
          icon="💬"
          title="아직 질문이 없습니다"
          description="지식 검색으로 프로젝트에 대해 물어보세요"
        />
      </div>

      {/* 빠른 접근: 프로젝트 */}
      <div className="w-full max-w-2xl">
        <h2
          className="text-sm font-semibold mb-4 uppercase tracking-wider"
          style={{ color: "var(--text-muted)", fontFamily: "var(--font-display)" }}
        >
          프로젝트
        </h2>
        <EmptyState
          icon="📁"
          title="첫 프로젝트를 만들어보세요"
          description="프로젝트를 만들면 회의, 노트, 자료를 체계적으로 관리할 수 있습니다"
          action={{ label: "프로젝트 만들기", href: "/new" }}
        />
      </div>
    </div>
  );
}
