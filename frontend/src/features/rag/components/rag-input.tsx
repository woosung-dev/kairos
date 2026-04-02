"use client";

import { useState } from "react";
import { useRagStore } from "../store";

interface RagInputProps {
  onSubmit: (query: string) => void;
}

export function RagInput({ onSubmit }: RagInputProps) {
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
    <div className="p-3 border-t" style={{ borderColor: "var(--border-subtle)" }}>
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
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="질문을 입력하세요..."
          disabled={isStreaming}
          className="flex-1 bg-transparent text-sm outline-none"
          style={{ color: "var(--text-primary)" }}
        />
        <button
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
    </div>
  );
}
