"use client";

import { RagChat } from "@/features/rag/components/rag-chat";
import { RagInput } from "@/features/rag/components/rag-input";
import { SearchScope } from "@/features/rag/components/search-scope";
import { useRagStream } from "@/features/rag/hooks";

export default function SearchPage() {
  const { ask } = useRagStream();

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b" style={{ borderColor: "var(--border-subtle)" }}>
        <h1
          className="text-lg font-semibold"
          style={{ fontFamily: "var(--font-display)", color: "var(--text-primary)" }}
        >
          지식 검색
        </h1>
        <SearchScope />
      </div>
      <RagChat />
      <RagInput onSubmit={ask} fabSafe />
    </div>
  );
}
