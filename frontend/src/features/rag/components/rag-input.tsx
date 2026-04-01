"use client";

import { useState } from "react";

interface RagInputProps {
  onSubmit: (query: string) => void;
  placeholder?: string;
}

export function RagInput({ onSubmit, placeholder = "질문을 입력하세요..." }: RagInputProps) {
  const [query, setQuery] = useState("");

  const handleSubmit = () => {
    if (!query.trim()) return;
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
        placeholder={placeholder}
        className="flex-1 bg-transparent text-sm outline-none"
        style={{ color: "var(--text-primary)" }}
      />
      <button
        onClick={handleSubmit}
        className="px-3 py-1.5 rounded text-xs font-medium transition-colors"
        style={{
          background: query.trim() ? "var(--accent)" : "var(--surface-active)",
          color: query.trim() ? "var(--background)" : "var(--text-muted)",
          borderRadius: "var(--radius-sm)",
        }}
      >
        전송
      </button>
    </div>
  );
}
