// 대시보드 추천 질문 카드 — Sprint 24 Wave 2 T-CMD-K-FIX (BUG-CURIOUS-002)
// 이전 dead-click: onClick → ask(q) 직접 호출 → palette 미열림.
// 변경: onClick → openCmdKWithQuery(q) → palette 열림 + query 자동 입력 + RAG 모드.
"use client";

import { useUIStore } from "@/store/ui";

const SUGGESTIONS = [
  "최근 회의에서 결정된 사항은?",
  "진행 중인 프로젝트 현황은?",
  "이번 주 액션 아이템은?",
  "보안 관련 논의 내용은?",
] as const;

export function DashboardSuggestions() {
  const openCmdKWithQuery = useUIStore((s) => s.openCmdKWithQuery);

  return (
    <div className="w-full max-w-2xl mb-12">
      <h2
        className="text-sm font-semibold mb-4 uppercase tracking-wider"
        style={{
          color: "var(--text-muted)",
          fontFamily: "var(--font-display)",
        }}
      >
        추천 질문
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {SUGGESTIONS.map((q) => (
          <button
            key={q}
            type="button"
            data-testid="dashboard-suggestion-button"
            onClick={() => openCmdKWithQuery(q)}
            className="text-left px-3 py-2.5 rounded border text-sm transition-colors"
            style={{
              borderColor: "var(--border-subtle)",
              color: "var(--text-secondary)",
              borderRadius: "var(--radius-sm)",
            }}
            onMouseOver={(e) =>
              (e.currentTarget.style.borderColor = "var(--accent)")
            }
            onMouseOut={(e) =>
              (e.currentTarget.style.borderColor = "var(--border-subtle)")
            }
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
