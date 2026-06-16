"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import { useRagStore } from "../store";
import { useSourceViewerStore } from "@/features/sources/store";
import { RagSources } from "./rag-sources";
import { MarkdownMessage } from "./markdown-message";
import { MessageActions } from "./message-actions";
import type { RagSource } from "../types";
import type { SourceDocument, HighlightChunk } from "@/features/sources/types";

/** RagSource → SourceDocument 변환 (snippet을 content로 사용, 추후 full doc fetch) */
function toSourceDocument(source: RagSource): SourceDocument {
  return {
    id: source.id,
    title: source.source,
    type: source.sourceType,
    content: source.text,
    projectId: "",
    createdAt: source.date,
  };
}

/** RagSource snippet에서 HighlightChunk 생성 (전체 텍스트가 하이라이트) */
function toHighlightChunk(source: RagSource, citationNumber: number): HighlightChunk {
  return {
    citationNumber,
    startOffset: 0,
    endOffset: source.text.length,
    text: source.text,
  };
}

export function RagChat() {
  // Sprint 29 R3 (rag-store): selector 별 구독 (전체 구독 시 searchFilter 등 무관 변경에도 re-render).
  const messages = useRagStore((s) => s.messages);
  const isStreaming = useRagStore((s) => s.isStreaming);
  const openSourceViewer = useSourceViewerStore((s) => s.open);
  const bottomRef = useRef<HTMLDivElement>(null);
  const [activeCitation, setActiveCitation] = useState<number | null>(null);

  // Sprint 29 R3 (rag-scroll): 매 토큰 smooth scroll 은 애니메이션 경합으로 떨림 발생 +
  // 사용자가 위로 스크롤해 읽는 중에도 강제로 끌어내렸다. 하단 근처일 때만 자동 스크롤하고,
  // 스트리밍 중엔 instant 로 떨림 제거.
  useEffect(() => {
    const anchor = bottomRef.current;
    const container = anchor?.parentElement;
    if (!anchor || !container) return;
    const nearBottom =
      container.scrollHeight - container.scrollTop - container.clientHeight < 120;
    if (!nearBottom) return;
    anchor.scrollIntoView({ behavior: isStreaming ? "auto" : "smooth" });
  }, [messages, isStreaming]);

  const handleCitationClick = useCallback(
    (num: number, sources?: RagSource[]) => {
      setActiveCitation((prev) => (prev === num ? null : num));

      // 소스가 있으면 소스 뷰어 열기
      const source = sources?.[num - 1];
      if (source) {
        openSourceViewer(
          toSourceDocument(source),
          [toHighlightChunk(source, num)],
        );
      }
    },
    [openSourceViewer],
  );

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center px-4">
        <p className="text-sm text-center" style={{ color: "var(--text-muted)" }}>
          프로젝트에 대해 질문하세요
        </p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
      {messages.map((msg) => (
        <div key={msg.id} className="space-y-1.5">
          <div
            className="flex gap-3"
            style={{
              justifyContent: msg.role === "user" ? "flex-end" : "flex-start",
            }}
          >
            <div
              className="max-w-[85%] px-3 py-2.5 rounded text-sm"
              style={{
                background:
                  msg.role === "user"
                    ? "var(--accent-subtle)"
                    : "var(--surface)",
                borderRadius: "var(--radius-md)",
                color: "var(--text-primary)",
                whiteSpace: "pre-wrap",
              }}
            >
              {msg.role === "assistant"
                ? msg.content && (
                    <MarkdownMessage
                      content={msg.content}
                      onCitationClick={(num) =>
                        handleCitationClick(num, msg.sources)
                      }
                      activeCitation={activeCitation}
                    />
                  )
                : msg.content}
              {msg.isStreaming && !msg.content && (
                <span
                  className="inline-block w-2 h-4 ml-0.5 animate-pulse"
                  style={{ background: "var(--accent)" }}
                />
              )}
            </div>
          </div>

          {/* AI 메시지 하단 액션 바 */}
          {msg.role === "assistant" && !msg.isStreaming && msg.content && (
            <div style={{ paddingLeft: 0 }}>
              <MessageActions content={msg.content} />
            </div>
          )}

          {msg.sources && msg.sources.length > 0 && (
            <RagSources sources={msg.sources} />
          )}
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
