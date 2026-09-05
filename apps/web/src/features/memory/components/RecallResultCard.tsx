// Recall 결과 카드 — title + atomic_notes_excerpt + match_type 배지
"use client";

import { Clock, Hash, Search } from "lucide-react";
import { formatDate } from "@/lib/format-date";
import type { MemoryRecallSource } from "../types";

interface RecallResultCardProps {
  source: MemoryRecallSource;
  onPromote?: (memoryId: string) => void;
}

export function RecallResultCard({
  source,
  onPromote,
}: RecallResultCardProps) {
  const MatchIcon = source.match_type === "vector" ? Search : Hash;
  const matchLabel =
    source.match_type === "vector" ? "의미 매칭" : "키워드 매칭";

  return (
    <article className="rounded-lg border border-border bg-card p-4 transition-colors hover:border-foreground/20">
      <header className="mb-2 flex items-start justify-between gap-2">
        <h3 className="text-sm font-medium">{source.title}</h3>
        <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
          <MatchIcon className="h-3 w-3" />
          {matchLabel}
        </span>
      </header>
      {source.atomic_notes_excerpt && (
        <p className="mb-3 text-sm text-muted-foreground">
          {source.atomic_notes_excerpt}
        </p>
      )}
      <footer className="flex items-center justify-between text-xs text-muted-foreground">
        <span className="inline-flex items-center gap-1">
          <Clock className="h-3 w-3" />
          {formatDate(source.created_at)}
        </span>
        {onPromote && (
          <button
            type="button"
            onClick={() => onPromote(source.memory_id)}
            className="text-xs text-foreground hover:underline"
          >
            팀으로 올리기
          </button>
        )}
      </footer>
    </article>
  );
}
