"use client";

import type { RagMessage } from "../types";
import { EmptyState } from "@/components/empty-state";

interface RagChatProps {
  messages: RagMessage[];
}

const FRESHNESS_LABELS: Record<string, string> = {
  recent: "최근",
  normal: "보통",
  stale: "오래됨",
};

const FRESHNESS_COLORS: Record<string, string> = {
  recent: "var(--success)",
  normal: "var(--text-muted)",
  stale: "var(--warning)",
};

export function RagChat({ messages }: RagChatProps) {
  if (messages.length === 0) {
    return (
      <EmptyState
        icon="🤖"
        title="대화를 시작하세요"
        description="프로젝트에 대해 질문하면 AI가 지식을 기반으로 답변합니다"
      />
    );
  }

  return (
    <div className="space-y-6">
      {messages.map((msg) => (
        <div key={msg.id} className="space-y-2">
          {/* 메시지 */}
          <div
            className="flex gap-3"
            style={{
              justifyContent: msg.role === "user" ? "flex-end" : "flex-start",
            }}
          >
            <div
              className="max-w-[80%] px-4 py-3 rounded"
              style={{
                background: msg.role === "user" ? "var(--accent-subtle)" : "var(--surface)",
                borderRadius: "var(--radius-md)",
              }}
            >
              <p className="text-sm" style={{ color: "var(--text-primary)" }}>
                {msg.content}
              </p>
            </div>
          </div>

          {/* 소스 인용 */}
          {msg.sources && msg.sources.length > 0 && (
            <div className="flex flex-wrap gap-2 pl-3">
              {msg.sources.map((source, i) => (
                <div
                  key={i}
                  className="flex items-center gap-2 px-2 py-1 rounded text-[10px]"
                  style={{
                    background: "var(--surface-hover)",
                    borderRadius: "var(--radius-sm)",
                  }}
                >
                  <span style={{ color: "var(--text-secondary)" }}>{source.title}</span>
                  <span
                    className="px-1 rounded"
                    style={{
                      color: FRESHNESS_COLORS[source.freshness],
                      fontFamily: "var(--font-mono)",
                    }}
                  >
                    {FRESHNESS_LABELS[source.freshness]}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
