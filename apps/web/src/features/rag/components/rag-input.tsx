"use client";

import { useState } from "react";
import { useRagStore } from "../store";

interface RagInputProps {
  onSubmit: (query: string) => void;
  /**
   * CAND-D: 전체 너비 composer(/search)는 우하단 피드백 FAB(fixed z-30)와 전송 버튼이
   * 겹쳐 클릭이 가로채진다. true 면 composer 우측에 FAB 폭만큼 gutter 를 둬 분리한다.
   * 우측 슬라이드 RAG 오버레이(z-40 패널)는 FAB 를 덮으므로 기본값 false.
   */
  fabSafe?: boolean;
}

export function RagInput({ onSubmit, fabSafe = false }: RagInputProps) {
  const [query, setQuery] = useState("");
  const { isStreaming } = useRagStore();

  const handleSubmit = () => {
    if (!query.trim() || isStreaming) return;
    onSubmit(query.trim());
    setQuery("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div
      className="p-3 border-t"
      style={{
        borderColor: "var(--border-subtle)",
        // FAB 폭(44px) + right-4(16px) + 여유 → 전송 버튼이 FAB footprint 를 벗어남.
        paddingRight: fabSafe ? "calc(0.75rem + 4rem)" : undefined,
      }}
    >
      <div
        className="flex items-center gap-2 px-3 py-2 rounded border"
        style={{
          background: "var(--surface)",
          borderColor: "var(--border)",
          borderRadius: "var(--radius-md)",
        }}
      >
        <input
          type="text"
          data-testid="rag-input"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="질문을 입력하세요..."
          disabled={isStreaming}
          className="flex-1 bg-transparent text-sm outline-none"
          style={{ color: "var(--text-primary)" }}
        />
        <button
          data-testid="rag-submit"
          onClick={handleSubmit}
          disabled={!query.trim() || isStreaming}
          className="px-3 py-1.5 rounded text-xs font-medium transition-colors"
          style={{
            background: query.trim() && !isStreaming ? "var(--accent)" : "var(--surface-active)",
            color: query.trim() && !isStreaming ? "var(--background)" : "var(--text-muted)",
            borderRadius: "var(--radius-sm)",
          }}
        >
          {isStreaming ? "..." : "전송"}
        </button>
      </div>
      {/* Sprint 6 FE-T7: RAG 검색 결과에서 권한 없는 프로젝트는 자동 제외됨 안내 */}
      <p
        className="mt-1.5 text-caption"
        style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}
      >
        Private 프로젝트는 명시적 멤버에게만 표시됩니다.
      </p>
    </div>
  );
}
