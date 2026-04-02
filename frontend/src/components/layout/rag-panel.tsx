"use client";

import { RagChat } from "@/features/rag/components/rag-chat";
import { RagInput } from "@/features/rag/components/rag-input";
import { SearchScope } from "@/features/rag/components/search-scope";
import { useRagStream } from "@/features/rag/hooks";
import { useRagStore } from "@/features/rag/store";

export function RagPanel() {
  const { ask } = useRagStream();
  const { messages, clearMessages } = useRagStore();

  return (
    <aside
      className="flex flex-col h-full w-[320px] shrink-0 border-l"
      style={{
        background: "var(--surface)",
        borderColor: "var(--border-subtle)",
      }}
    >
      {/* 헤더 */}
      <div
        className="px-4 py-3 border-b flex items-center justify-between"
        style={{ borderColor: "var(--border-subtle)" }}
      >
        <h2
          className="text-sm font-semibold"
          style={{
            fontFamily: "var(--font-display)",
            color: "var(--text-primary)",
          }}
        >
          지식 검색
        </h2>
        {messages.length > 0 && (
          <button
            onClick={clearMessages}
            className="text-[10px] px-2 py-0.5 rounded"
            style={{
              color: "var(--text-muted)",
              background: "var(--surface-hover)",
              borderRadius: "var(--radius-sm)",
            }}
          >
            초기화
          </button>
        )}
      </div>

      {/* 필터 */}
      <SearchScope />

      {/* 채팅 영역 */}
      <RagChat />

      {/* 입력 */}
      <RagInput onSubmit={ask} />
    </aside>
  );
}
