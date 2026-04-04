"use client";

import { useState } from "react";

/* ── 출처 색상 시스템 ── */

interface SourceStyle {
  background: string;
  color: string;
}

const SOURCE_STYLES: Record<number, SourceStyle> = {
  1: { background: "var(--accent-subtle)", color: "var(--accent)" },
  2: { background: "rgba(167,139,250,0.1)", color: "#A78BFA" },
  3: { background: "rgba(251,191,36,0.1)", color: "#FBBF24" },
};

/* ── Mock 타입 ── */

interface MeetingAction {
  id: string;
  title: string;
  assignee: string;
  dueDate: string;
  isDone: boolean;
  sourceRef: number;
}

/* ── Mock 데이터 ── */

const MOCK_ACTIONS: MeetingAction[] = [
  {
    id: "ma-001",
    title: "RAG 캐시 레이어 구현 (6-Layer 아키텍처 1단계)",
    assignee: "김민수",
    dueDate: "2026-04-14",
    isDone: false,
    sourceRef: 1,
  },
  {
    id: "ma-002",
    title: "디자인 시스템 v2 마이그레이션 계획서 작성",
    assignee: "이지은",
    dueDate: "2026-04-10",
    isDone: false,
    sourceRef: 2,
  },
  {
    id: "ma-003",
    title: "Figma 토큰 자동 동기화 PoC 결과 공유",
    assignee: "최수진",
    dueDate: "2026-04-05",
    isDone: true,
    sourceRef: 2,
  },
  {
    id: "ma-004",
    title: "보안통신 모듈 요구사항 문서 정리",
    assignee: "박현우",
    dueDate: "2026-04-07",
    isDone: false,
    sourceRef: 3,
  },
];

/* ── 컴포넌트 ── */

export function ActionView() {
  const [actions, setActions] = useState(MOCK_ACTIONS);

  function handleToggle(actionId: string) {
    setActions((prev) =>
      prev.map((a) => (a.id === actionId ? { ...a, isDone: !a.isDone } : a))
    );
  }

  const doneCount = actions.filter((a) => a.isDone).length;
  const totalCount = actions.length;

  return (
    <div className="space-y-4">
      {/* 진행률 */}
      <div className="flex items-center gap-3">
        <div
          className="flex-1 h-1.5 rounded-full overflow-hidden"
          style={{ background: "var(--surface-active)" }}
        >
          <div
            className="h-full rounded-full transition-all"
            style={{
              width: `${totalCount > 0 ? (doneCount / totalCount) * 100 : 0}%`,
              background: "var(--accent)",
            }}
          />
        </div>
        <span className="text-xs shrink-0" style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
          {doneCount}/{totalCount}
        </span>
      </div>

      {/* 액션 리스트 */}
      <div className="space-y-2">
        {actions.map((action) => (
          <ActionRow
            key={action.id}
            action={action}
            onToggle={() => handleToggle(action.id)}
          />
        ))}
      </div>
    </div>
  );
}

/* ── 서브 컴포넌트 ── */

function ActionRow({ action, onToggle }: { action: MeetingAction; onToggle: () => void }) {
  const sourceStyle = SOURCE_STYLES[action.sourceRef] ?? SOURCE_STYLES[1];

  return (
    <div
      className="flex items-start gap-3 p-3 rounded-lg border transition-colors"
      style={{
        background: "var(--surface)",
        borderColor: "var(--border-subtle)",
        borderRadius: "var(--radius-lg)",
      }}
    >
      {/* 체크박스 */}
      <input
        type="checkbox"
        checked={action.isDone}
        onChange={onToggle}
        className="shrink-0 w-4 h-4 mt-0.5 rounded accent-current"
        style={{ accentColor: "var(--accent)", cursor: "pointer" }}
      />

      {/* 내용 */}
      <div className="flex-1 min-w-0">
        <p
          className="text-sm"
          style={{
            color: action.isDone ? "var(--text-muted)" : "var(--text-primary)",
            textDecoration: action.isDone ? "line-through" : "none",
          }}
        >
          {action.title}
        </p>
        <div className="flex items-center gap-3 mt-1">
          <span className="text-[11px]" style={{ color: "var(--text-muted)" }}>
            {action.assignee}
          </span>
          <span className="text-[11px]" style={{ color: "var(--text-muted)" }}>
            &middot;
          </span>
          <span
            className="text-[11px]"
            style={{
              color: isOverdue(action.dueDate) && !action.isDone ? "var(--error)" : "var(--text-muted)",
              fontFamily: "var(--font-mono)",
            }}
          >
            {action.dueDate}
          </span>

          {/* 출처 링크 */}
          <span
            className="px-1.5 py-0.5 rounded text-[10px] font-mono font-medium ml-auto"
            style={{
              background: sourceStyle.background,
              color: sourceStyle.color,
            }}
          >
            [{action.sourceRef}]
          </span>
        </div>
      </div>
    </div>
  );
}

/** 마감일이 지났는지 확인 */
function isOverdue(dateStr: string): boolean {
  const dueDate = new Date(dateStr);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return dueDate < today;
}
