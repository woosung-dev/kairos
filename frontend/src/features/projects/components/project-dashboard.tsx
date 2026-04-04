"use client";

import { useState } from "react";
import { InsightCard } from "./insight-card";
import type { UUID } from "@/types";

/* ── Mock 타입 ── */

interface MockMeetingNote {
  id: UUID;
  type: "meeting" | "note";
  title: string;
  summary: string;
  date: string;
  participants: number;
}

interface MockAction {
  id: UUID;
  title: string;
  assignee: string;
  dueDate: string;
  isDone: boolean;
}

/* ── Mock 데이터 ── */

const MOCK_PROJECT = {
  id: "proj-001",
  title: "Q2 제품 로드맵",
  description: "2분기 제품 전략 및 로드맵 수립",
  status: "active" as const,
  sourceCount: 12,
  meetingCount: 5,
  actionCount: 8,
};

const MOCK_INSIGHT = "보안통신 주제가 최근 회의에서 3회 반복 언급되었습니다. Q1 교훈 문서와 유사한 패턴이 감지되어 별도 프로젝트 분리를 제안합니다.";

const MOCK_RECENT_ITEMS: MockMeetingNote[] = [
  {
    id: "mt-001",
    type: "meeting",
    title: "주간 스프린트 리뷰",
    summary: "Sprint 4 배포 완료 및 Sprint 5 계획 논의. 인프라 비용 최적화 안건 추가.",
    date: "2026-03-31",
    participants: 4,
  },
  {
    id: "mt-002",
    type: "meeting",
    title: "디자인 시스템 워크숍",
    summary: "컴포넌트 라이브러리 통합 방안 결정. Figma 토큰 자동 동기화 도입 합의.",
    date: "2026-03-28",
    participants: 3,
  },
  {
    id: "nt-001",
    type: "note",
    title: "경쟁사 분석 메모",
    summary: "Notion AI, Mem, Reflect 기능 비교. RAG 기반 검색이 차별점으로 작용할 수 있음.",
    date: "2026-03-27",
    participants: 0,
  },
];

const MOCK_ACTIONS: MockAction[] = [
  { id: "act-001", title: "RAG 파이프라인 성능 테스트", assignee: "김민수", dueDate: "2026-04-05", isDone: false },
  { id: "act-002", title: "디자인 시스템 문서 업데이트", assignee: "이지은", dueDate: "2026-04-03", isDone: true },
  { id: "act-003", title: "인프라 비용 보고서 작성", assignee: "박현우", dueDate: "2026-04-07", isDone: false },
  { id: "act-004", title: "사용자 피드백 분석", assignee: "최수진", dueDate: "2026-04-04", isDone: false },
];

/* ── 상태 라벨 ── */

const STATUS_LABELS: Record<string, string> = {
  active: "진행 중",
  completed: "완료",
  archived: "보관",
};

const STATUS_BG: Record<string, string> = {
  active: "var(--accent-subtle)",
  completed: "rgba(52,211,153,0.1)",
  archived: "rgba(156,163,175,0.1)",
};

const STATUS_COLOR: Record<string, string> = {
  active: "var(--accent)",
  completed: "var(--success)",
  archived: "var(--text-muted)",
};

/* ── 컴포넌트 ── */

interface ProjectDashboardProps {
  projectId: string;
}

export function ProjectDashboard({ projectId }: ProjectDashboardProps) {
  const [actions, setActions] = useState(MOCK_ACTIONS);

  /* Mock 기반이므로 projectId는 향후 API 연동 시 활용 */
  void projectId;

  const project = MOCK_PROJECT;
  const hasContent = MOCK_RECENT_ITEMS.length >= 3;

  function handleToggleAction(actionId: string) {
    setActions((prev) =>
      prev.map((a) => (a.id === actionId ? { ...a, isDone: !a.isDone } : a))
    );
  }

  /* 온보딩 뷰: 콘텐츠 3개 미만 시 */
  if (!hasContent) {
    return (
      <div className="p-6">
        <DashboardHeader project={project} />
        <OnboardingView />
      </div>
    );
  }

  return (
    <div className="p-6">
      <DashboardHeader project={project} />

      {/* 프로액티브 인사이트 */}
      <div className="mb-6">
        <InsightCard text={MOCK_INSIGHT} />
      </div>

      {/* 2컬럼 그리드 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* 좌: 최근 회의/노트 */}
        <div className="space-y-3">
          <h2
            className="text-sm font-semibold mb-1"
            style={{ color: "var(--text-secondary)", fontFamily: "var(--font-display)" }}
          >
            최근 회의 &middot; 노트
          </h2>
          {MOCK_RECENT_ITEMS.map((item) => (
            <RecentItemCard key={item.id} item={item} />
          ))}
        </div>

        {/* 우: 이번 주 액션 */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <h2
              className="text-sm font-semibold"
              style={{ color: "var(--text-secondary)", fontFamily: "var(--font-display)" }}
            >
              이번 주 액션
            </h2>
            <button
              className="text-xs transition-colors"
              style={{ color: "var(--accent)", cursor: "pointer", minHeight: "44px" }}
            >
              내보내기
            </button>
          </div>
          <div className="space-y-2">
            {actions.map((action) => (
              <ActionRow
                key={action.id}
                action={action}
                onToggle={() => handleToggleAction(action.id)}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── 서브 컴포넌트 ── */

function DashboardHeader({ project }: { project: typeof MOCK_PROJECT }) {
  const metaItems = [
    { label: "소스", value: project.sourceCount },
    { label: "회의", value: project.meetingCount },
    { label: "액션", value: project.actionCount },
  ];

  return (
    <div className="mb-6">
      <div className="flex items-center gap-3 mb-2">
        <h1
          className="text-2xl font-bold"
          style={{ fontFamily: "var(--font-display)", color: "var(--text-primary)" }}
        >
          {project.title}
        </h1>
        <span
          className="px-2 py-0.5 rounded-full text-xs font-medium"
          style={{
            background: STATUS_BG[project.status] ?? "var(--accent-subtle)",
            color: STATUS_COLOR[project.status] ?? "var(--accent)",
          }}
        >
          {STATUS_LABELS[project.status] ?? project.status}
        </span>
      </div>
      {project.description && (
        <p className="text-sm mb-3" style={{ color: "var(--text-secondary)" }}>
          {project.description}
        </p>
      )}
      <div className="flex items-center gap-4">
        {metaItems.map((m) => (
          <span key={m.label} className="text-xs" style={{ color: "var(--text-muted)" }}>
            {m.label}{" "}
            <strong style={{ color: "var(--text-primary)", fontFamily: "var(--font-mono)" }}>
              {m.value}
            </strong>
          </span>
        ))}
      </div>
    </div>
  );
}

function RecentItemCard({ item }: { item: MockMeetingNote }) {
  const icon = item.type === "meeting" ? "🎙️" : "📝";
  const typeLabel = item.type === "meeting" ? "회의" : "노트";

  return (
    <div
      className="p-4 rounded-lg border transition-colors"
      style={{
        background: "var(--surface)",
        borderColor: "var(--border-subtle)",
        borderRadius: "var(--radius-lg)",
        cursor: "pointer",
      }}
      onMouseOver={(e) => (e.currentTarget.style.borderColor = "var(--accent)")}
      onMouseOut={(e) => (e.currentTarget.style.borderColor = "var(--border-subtle)")}
    >
      <div className="flex items-start gap-3">
        <span className="text-base shrink-0 mt-0.5">{icon}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-sm font-semibold truncate" style={{ color: "var(--text-primary)" }}>
              {item.title}
            </h3>
            <span
              className="shrink-0 px-1.5 py-0.5 rounded-full text-[10px]"
              style={{
                background: "var(--surface-active)",
                color: "var(--text-muted)",
              }}
            >
              {typeLabel}
            </span>
          </div>
          <p className="text-xs line-clamp-2 mb-2" style={{ color: "var(--text-secondary)" }}>
            {item.summary}
          </p>
          <div className="flex items-center gap-3 text-[10px]" style={{ color: "var(--text-muted)" }}>
            <span>{item.date}</span>
            {item.type === "meeting" && item.participants > 0 && (
              <span>참석자 {item.participants}명</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function ActionRow({ action, onToggle }: { action: MockAction; onToggle: () => void }) {
  return (
    <div
      className="flex items-center gap-3 px-3 py-2 rounded-lg border transition-colors"
      style={{
        background: "var(--surface)",
        borderColor: "var(--border-subtle)",
        borderRadius: "var(--radius-lg)",
      }}
    >
      <input
        type="checkbox"
        checked={action.isDone}
        onChange={onToggle}
        className="shrink-0 w-4 h-4 rounded accent-current"
        style={{ accentColor: "var(--accent)", cursor: "pointer", minHeight: "44px", minWidth: "16px" }}
      />
      <div className="flex-1 min-w-0">
        <p
          className="text-sm truncate"
          style={{
            color: action.isDone ? "var(--text-muted)" : "var(--text-primary)",
            textDecoration: action.isDone ? "line-through" : "none",
          }}
        >
          {action.title}
        </p>
        <div className="flex items-center gap-2 text-[10px]" style={{ color: "var(--text-muted)" }}>
          <span>{action.assignee}</span>
          <span>&middot;</span>
          <span>{action.dueDate}</span>
        </div>
      </div>
    </div>
  );
}

function OnboardingView() {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <span className="text-5xl mb-6">🚀</span>
      <h2
        className="text-xl font-bold mb-2"
        style={{ fontFamily: "var(--font-display)", color: "var(--text-primary)" }}
      >
        프로젝트를 시작하세요
      </h2>
      <p className="text-sm mb-8 max-w-md" style={{ color: "var(--text-muted)" }}>
        첫 회의를 녹음하거나 노트를 작성해보세요. AI가 자동으로 요약하고 지식을 구조화합니다.
      </p>
      <div className="flex items-center gap-3">
        <a
          href="/new"
          className="px-5 py-2.5 rounded text-sm font-medium transition-colors"
          style={{
            background: "var(--accent)",
            color: "var(--background)",
            borderRadius: "var(--radius-sm)",
            minHeight: "44px",
            display: "inline-flex",
            alignItems: "center",
            cursor: "pointer",
          }}
        >
          🎙️ 회의 녹음
        </a>
        <a
          href="/notes"
          className="px-5 py-2.5 rounded text-sm font-medium transition-colors border"
          style={{
            borderColor: "var(--border)",
            color: "var(--text-primary)",
            borderRadius: "var(--radius-sm)",
            minHeight: "44px",
            display: "inline-flex",
            alignItems: "center",
            cursor: "pointer",
          }}
        >
          📝 노트 작성
        </a>
      </div>
    </div>
  );
}
