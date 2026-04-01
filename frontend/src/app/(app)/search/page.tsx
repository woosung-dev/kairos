"use client";

import { RagChat } from "@/features/rag/components/rag-chat";
import { RagInput } from "@/features/rag/components/rag-input";
import { SearchScope } from "@/features/rag/components/search-scope";

export default function SearchPage() {
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
      <div className="flex-1 overflow-y-auto p-4">
        <RagChat messages={[]} />
      </div>
      <div className="p-4 border-t" style={{ borderColor: "var(--border-subtle)" }}>
        <RagInput onSubmit={() => {}} />
      </div>
    </div>
  );
}
