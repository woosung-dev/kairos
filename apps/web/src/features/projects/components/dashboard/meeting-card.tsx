// 대시보드 최근 항목의 회의 카드 — /meetings/{id} 링크 (BL-AV-1 분해)
"use client";

import Link from "next/link";
import { Mic } from "lucide-react";
import type { Meeting } from "@/features/meetings/types";

export function MeetingCard({ meeting }: { meeting: Meeting }) {
  const displayDate = meeting.recordedAt
    ? new Date(meeting.recordedAt).toLocaleDateString("ko-KR")
    : new Date(meeting.createdAt).toLocaleDateString("ko-KR");

  return (
    <Link
      href={`/meetings/${meeting.id}`}
      data-testid="meeting-card"
      className="block p-4 rounded-lg border transition-colors"
      style={{
        background: "var(--surface)",
        borderColor: "var(--border-subtle)",
        borderRadius: "var(--radius-lg)",
      }}
    >
      <div className="flex items-start gap-3">
        <Mic className="w-4 h-4 shrink-0 mt-0.5" style={{ color: "var(--text-muted)" }} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-sm font-semibold truncate" style={{ color: "var(--text-primary)" }}>
              {meeting.title}
            </h3>
            <span
              className="shrink-0 px-1.5 py-0.5 rounded-full text-micro"
              style={{
                background: "var(--surface-active)",
                color: "var(--text-muted)",
              }}
            >
              회의
            </span>
          </div>
          <div className="text-micro" style={{ color: "var(--text-muted)" }}>
            {displayDate}
            {meeting.actionItemCount > 0 && (
              <span className="ml-2">액션 {meeting.actionItemCount}개</span>
            )}
          </div>
        </div>
      </div>
    </Link>
  );
}
