// 대시보드 최근 항목의 노트 카드 — /notes/{id} 링크 (BL-AV-1 분해)
"use client";

import Link from "next/link";
import { StickyNote } from "lucide-react";
import type { Note } from "@/features/notes/types";
import { formatDate } from "@/lib/format-date";

export function NoteCard({ note }: { note: Note }) {
  const displayDate = formatDate(note.createdAt);

  return (
    <Link
      href={`/notes/${note.id}`}
      className="block p-4 rounded-lg border transition-colors"
      style={{
        background: "var(--surface)",
        borderColor: "var(--border-subtle)",
        borderRadius: "var(--radius-lg)",
      }}
    >
      <div className="flex items-start gap-3">
        <StickyNote className="w-4 h-4 shrink-0 mt-0.5" style={{ color: "var(--text-muted)" }} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-sm font-semibold truncate" style={{ color: "var(--text-primary)" }}>
              {note.title}
            </h3>
            <span
              className="shrink-0 px-1.5 py-0.5 rounded-full text-micro"
              style={{
                background: "var(--surface-active)",
                color: "var(--text-muted)",
              }}
            >
              노트
            </span>
          </div>
          {note.plainText && (
            <p className="text-xs line-clamp-1 mb-1" style={{ color: "var(--text-secondary)" }}>
              {note.plainText}
            </p>
          )}
          <div className="text-micro" style={{ color: "var(--text-muted)" }}>
            {displayDate}
          </div>
        </div>
      </div>
    </Link>
  );
}
