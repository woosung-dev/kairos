"use client";

import { useEffect, useRef, useCallback, useState, type ReactNode } from "react";
import { useRagStore } from "../store";
import { RagSources } from "./rag-sources";
import { CitationBadge } from "./citation-badge";
import { MessageActions } from "./message-actions";

/** [1], [2] 등 인라인 출처 표기를 감지하여 CitationBadge로 변환 */
function renderContentWithCitations(
  content: string,
  onCitationClick: (num: number) => void,
  activeCitation: number | null,
): ReactNode[] {
  const parts: ReactNode[] = [];
  const regex = /\[(\d+)\]/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null = null;

  while ((match = regex.exec(content)) !== null) {
    // 매치 앞 텍스트
    if (match.index > lastIndex) {
      parts.push(content.slice(lastIndex, match.index));
    }
    const citNum = parseInt(match[1], 10);
    parts.push(
      <CitationBadge
        key={`cit-${match.index}`}
        number={citNum}
        onClick={() => onCitationClick(citNum)}
        isActive={activeCitation === citNum}
      />,
    );
    lastIndex = regex.lastIndex;
  }

  // 나머지 텍스트
  if (lastIndex < content.length) {
    parts.push(content.slice(lastIndex));
  }

  return parts;
}

export function RagChat() {
  const { messages, isStreaming } = useRagStore();
  const bottomRef = useRef<HTMLDivElement>(null);
  const [activeCitation, setActiveCitation] = useState<number | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isStreaming]);

  const handleCitationClick = useCallback((num: number) => {
    setActiveCitation((prev) => (prev === num ? null : num));
  }, []);

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
                ? renderContentWithCitations(
                    msg.content,
                    handleCitationClick,
                    activeCitation,
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
