"use client";

import { RagChat } from "@/features/rag/components/rag-chat";
import { RagInput } from "@/features/rag/components/rag-input";
import { SearchScope } from "@/features/rag/components/search-scope";
import { useRagStream } from "@/features/rag/hooks";
import { useRagStore } from "@/features/rag/store";

interface RagPanelProps {
  /** 오버레이로 열렸을 때 닫기 버튼. 미지정이면(페이지 임베드) 렌더하지 않는다. */
  onClose?: () => void;
}

export function RagPanel({ onClose }: RagPanelProps) {
  const { ask } = useRagStream();
  const { messages, clearMessages } = useRagStore();

  return (
    <div
      className="flex flex-col h-full w-full shrink-0"
      style={{
        background: "var(--surface)",
      }}
    >
      {/* 헤더 — 오버레이일 때 닫기 버튼까지 여기서 그린다 (이전엔 panel-layout 이 같은 제목의
          헤더를 한 번 더 그려 "지식 검색" 이 두 줄로 겹쳐 보였다) */}
      <div
        className="px-4 py-3 border-b flex items-center justify-between gap-2"
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
        <div className="flex items-center gap-1.5">
          {messages.length > 0 && (
            <button
              type="button"
              onClick={clearMessages}
              className="text-micro px-2 py-1 rounded cursor-pointer"
              style={{
                color: "var(--text-muted)",
                background: "var(--surface-hover)",
                borderRadius: "var(--radius-sm)",
              }}
            >
              초기화
            </button>
          )}
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              className="p-1 rounded transition-colors hover:opacity-80 cursor-pointer"
              style={{ color: "var(--text-muted)" }}
              aria-label="AI 검색 패널 닫기"
            >
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
                <path d="M1 1l12 12M13 1L1 13" />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* 필터 */}
      <SearchScope />

      {/* 채팅 영역 */}
      <RagChat />

      {/* 입력 */}
      <RagInput onSubmit={ask} />
    </div>
  );
}
