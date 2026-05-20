// 회의 요약 카드 — AI 요약 + 결정사항 + 토픽 (Sprint 24 Wave 2 T-OBN-05 D 옵션 적용)
"use client";

import type { MeetingSummary as MeetingSummaryType } from "../types";
import { EmptyState } from "@/components/empty-state";

interface MeetingSummaryProps {
  summary: MeetingSummaryType | null;
}

export function MeetingSummary({ summary }: MeetingSummaryProps) {
  if (!summary) {
    return (
      <EmptyState
        icon="📋"
        title="요약이 아직 없습니다"
        description="AI가 회의 내용을 분석하면 요약이 생성됩니다"
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* AI 요약 */}
      <div
        className="p-4 rounded border"
        style={{
          background: "var(--surface)",
          borderColor: "var(--border-subtle)",
          borderRadius: "var(--radius-md)",
        }}
      >
        <h3
          className="text-sm font-semibold mb-2"
          style={{ color: "var(--text-primary)", fontFamily: "var(--font-display)" }}
        >
          요약
        </h3>
        <p className="text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
          {summary.summary}
        </p>
      </div>

      {/* 결정사항 */}
      {summary.keyDecisions.length > 0 && (
        <div
          className="p-4 rounded border"
          style={{
            background: "var(--surface)",
            borderColor: "var(--border-subtle)",
            borderRadius: "var(--radius-md)",
          }}
        >
          <h3
            className="text-sm font-semibold mb-2"
            style={{ color: "var(--text-primary)", fontFamily: "var(--font-display)" }}
          >
            결정사항
          </h3>
          <ul className="space-y-1">
            {summary.keyDecisions.map((decision, i) => (
              <li key={i} className="flex items-start gap-2 text-sm" style={{ color: "var(--text-secondary)" }}>
                <span style={{ color: "var(--accent)" }}>•</span>
                <span>{decision}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 토픽 태그 */}
      {summary.topics.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {summary.topics.map((topic) => (
            <span
              key={topic}
              className="px-2 py-1 rounded-full text-xs"
              style={{
                background: "var(--surface-active)",
                color: "var(--text-secondary)",
              }}
            >
              {topic}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
