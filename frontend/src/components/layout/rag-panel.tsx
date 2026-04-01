"use client";

import { useState } from "react";

export function RagPanel() {
  const [query, setQuery] = useState("");

  return (
    <aside
      className="flex flex-col h-full w-[320px] shrink-0 border-l"
      style={{
        background: "var(--surface)",
        borderColor: "var(--border-subtle)",
      }}
    >
      {/* 헤더 */}
      <div className="px-4 py-3 border-b" style={{ borderColor: "var(--border-subtle)" }}>
        <h2 className="text-sm font-semibold" style={{ fontFamily: "var(--font-display)", color: "var(--text-primary)" }}>
          지식 검색
        </h2>
      </div>

      {/* 채팅 영역 (빈 상태) */}
      <div className="flex-1 flex items-center justify-center px-4">
        <p className="text-sm text-center" style={{ color: "var(--text-muted)" }}>
          프로젝트에 대해 질문하세요...
        </p>
      </div>

      {/* 입력 필드 */}
      <div className="p-3 border-t" style={{ borderColor: "var(--border-subtle)" }}>
        <div
          className="flex items-center gap-2 px-3 py-2 rounded"
          style={{
            background: "var(--surface-hover)",
            borderRadius: "var(--radius-md)",
          }}
        >
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="질문을 입력하세요..."
            className="flex-1 bg-transparent text-sm outline-none"
            style={{ color: "var(--text-primary)" }}
          />
          <button
            className="px-2 py-1 rounded text-xs font-medium"
            style={{
              background: "var(--accent)",
              color: "var(--background)",
              borderRadius: "var(--radius-sm)",
            }}
          >
            전송
          </button>
        </div>
      </div>
    </aside>
  );
}
