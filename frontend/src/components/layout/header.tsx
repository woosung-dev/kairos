"use client";

import { Search } from "lucide-react";
import { useUIStore } from "@/store/ui";

export function Header() {
  const { toggleSidebar, toggleRagOverlay } = useUIStore();

  return (
    <header
      className="flex items-center justify-between px-4 py-2 border-b shrink-0 gap-3"
      style={{
        background: "var(--surface)",
        borderColor: "var(--border-subtle)",
      }}
    >
      {/* 좌측: 사이드바 토글 + breadcrumb */}
      <div className="flex items-center gap-3 shrink-0">
        <button
          onClick={toggleSidebar}
          className="p-1.5 rounded transition-colors hover:opacity-80"
          style={{ color: "var(--text-secondary)" }}
          aria-label="사이드바 토글"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <rect x="2" y="3" width="12" height="1.5" rx="0.5" />
            <rect x="2" y="7.25" width="12" height="1.5" rx="0.5" />
            <rect x="2" y="11.5" width="12" height="1.5" rx="0.5" />
          </svg>
        </button>
        <span className="text-sm" style={{ color: "var(--text-secondary)" }}>
          Kairos
        </span>
      </div>

      {/* 중앙: RAG 검색바 스타일 (클릭 시 RAG 오버레이 열기) */}
      <button
        onClick={toggleRagOverlay}
        className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm flex-1 max-w-md mx-auto transition-colors hover:opacity-90"
        style={{
          background: "var(--surface-hover)",
          color: "var(--text-muted)",
          borderRadius: "var(--radius-lg)",
          border: "1px solid var(--border-subtle)",
        }}
      >
        <Search size={14} style={{ color: "var(--text-muted)", flexShrink: 0 }} />
        <span className="truncate">팀 지식 검색...</span>
        <kbd
          className="ml-auto px-1.5 py-0.5 rounded text-[10px] shrink-0"
          style={{
            background: "var(--surface-active)",
            color: "var(--text-muted)",
            borderRadius: "var(--radius-sm)",
            fontFamily: "var(--font-mono)",
          }}
        >
          ⌘K
        </kbd>
      </button>

      {/* 우측: 아바타만 (RAG 토글 버튼 제거 — 검색바가 대체) */}
      <div className="flex items-center gap-2 shrink-0">
        {/* Clerk UserButton 자리 — Clerk 없이도 빌드되도록 플레이스홀더 */}
        <div
          className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-medium"
          style={{
            background: "var(--accent-subtle)",
            color: "var(--accent)",
            borderRadius: "var(--radius-full)",
          }}
        >
          U
        </div>
      </div>
    </header>
  );
}
