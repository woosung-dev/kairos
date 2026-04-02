"use client";

import { useEffect, useRef } from "react";
import { useRagStore } from "../store";
import { RagSources } from "./rag-sources";

export function RagChat() {
  const { messages, isStreaming } = useRagStore();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isStreaming]);

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
              {msg.content}
              {msg.isStreaming && !msg.content && (
                <span
                  className="inline-block w-2 h-4 ml-0.5 animate-pulse"
                  style={{ background: "var(--accent)" }}
                />
              )}
            </div>
          </div>

          {msg.sources && msg.sources.length > 0 && (
            <RagSources sources={msg.sources} />
          )}
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
