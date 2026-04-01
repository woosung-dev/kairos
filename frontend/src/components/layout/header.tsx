"use client";

import { useUIStore } from "@/store/ui";

export function Header() {
  const { toggleSidebar, toggleRagPanel, toggleCmdK } = useUIStore();

  return (
    <header
      className="flex items-center justify-between px-4 py-2 border-b shrink-0"
      style={{
        background: "var(--surface)",
        borderColor: "var(--border-subtle)",
      }}
    >
      {/* 좌측: 사이드바 토글 + breadcrumb */}
      <div className="flex items-center gap-3">
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

      {/* 중앙: 검색 */}
      <button
        onClick={toggleCmdK}
        className="flex items-center gap-2 px-3 py-1.5 rounded text-xs"
        style={{
          background: "var(--surface-hover)",
          color: "var(--text-muted)",
          borderRadius: "var(--radius-sm)",
        }}
      >
        <span>검색...</span>
        <kbd
          className="px-1.5 py-0.5 rounded text-[10px]"
          style={{
            background: "var(--surface-active)",
            borderRadius: "var(--radius-sm)",
            fontFamily: "var(--font-mono)",
          }}
        >
          ⌘K
        </kbd>
      </button>

      {/* 우측: RAG 패널 토글 + 아바타 */}
      <div className="flex items-center gap-2">
        <button
          onClick={toggleRagPanel}
          className="p-1.5 rounded transition-colors hover:opacity-80"
          style={{ color: "var(--text-secondary)" }}
          aria-label="RAG 패널 토글"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M2 3a1 1 0 011-1h10a1 1 0 011 1v10a1 1 0 01-1 1H3a1 1 0 01-1-1V3zm10 0H9v10h4V3z" />
          </svg>
        </button>
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
