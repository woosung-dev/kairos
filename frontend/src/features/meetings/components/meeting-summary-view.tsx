"use client";

import { ClipboardList } from "lucide-react";
import type { MeetingSummary } from "../types";

/* ── Props ── */

interface MeetingSummaryViewProps {
  summary: MeetingSummary | null;
  onSwitchToTranscript: () => void;
}

/* ── 컴포넌트 ── */

export function MeetingSummaryView({ summary, onSwitchToTranscript }: MeetingSummaryViewProps) {
  /* 요약 데이터 없음 */
  if (!summary) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <ClipboardList className="w-10 h-10 mb-4" style={{ color: "var(--text-muted)" }} />
        <h3
          className="text-lg font-semibold mb-2"
          style={{ color: "var(--text-primary)", fontFamily: "var(--font-display)" }}
        >
          요약 정보가 없습니다
        </h3>
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          AI 분석이 완료되면 요약이 자동으로 생성됩니다
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 요약 블록 */}
      <div
        className="p-4 rounded-lg border"
        style={{
          background: "var(--surface)",
          borderColor: "var(--border-subtle)",
          borderRadius: "var(--radius-lg)",
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

      {/* 핵심 결정사항 */}
      {summary.keyDecisions.length > 0 && (
        <div
          className="p-4 rounded-lg border"
          style={{
            background: "var(--surface)",
            borderColor: "var(--border-subtle)",
            borderRadius: "var(--radius-lg)",
          }}
        >
          <h3
            className="text-sm font-semibold mb-3"
            style={{ color: "var(--text-primary)", fontFamily: "var(--font-display)" }}
          >
            핵심 결정사항
          </h3>
          <ul className="space-y-2">
            {summary.keyDecisions.map((decision, idx) => (
              <li key={idx} className="flex items-start gap-2">
                <span
                  className="shrink-0 mt-0.5 text-xs"
                  style={{ color: "var(--accent)" }}
                >
                  •
                </span>
                <span className="text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                  {decision}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 주제 태그 */}
      {summary.topics.length > 0 && (
        <div
          className="p-4 rounded-lg border"
          style={{
            background: "var(--surface)",
            borderColor: "var(--border-subtle)",
            borderRadius: "var(--radius-lg)",
          }}
        >
          <h3
            className="text-sm font-semibold mb-3"
            style={{ color: "var(--text-primary)", fontFamily: "var(--font-display)" }}
          >
            주제
          </h3>
          <div className="flex flex-wrap gap-2">
            {summary.topics.map((topic, idx) => (
              <span
                key={idx}
                className="px-2 py-1 rounded text-xs"
                style={{
                  background: "var(--accent-subtle)",
                  color: "var(--accent)",
                  borderRadius: "var(--radius-sm)",
                }}
              >
                {topic}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* 트랜스크립트 전체 보기 링크 */}
      <div className="flex justify-end">
        <button
          onClick={onSwitchToTranscript}
          className="text-xs transition-colors"
          style={{ color: "var(--accent)", cursor: "pointer", minHeight: "44px" }}
        >
          트랜스크립트 전체 보기 →
        </button>
      </div>
    </div>
  );
}
