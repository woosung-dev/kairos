"use client";

import Link from "next/link";
import { useProject } from "../hooks";
import { useActionItems, useUpdateActionItem } from "@/features/actions/hooks";
import { useMeetings } from "@/features/meetings/hooks";
import { useNotes } from "@/features/notes/hooks";
import { useWorkspaceStore } from "@/features/workspaces/store";
import type { Project, ProjectStatus } from "../types";
import type { ActionItem, ActionStatus } from "@/features/actions/types";
import type { Meeting } from "@/features/meetings/types";
import type { Note } from "@/features/notes/types";

/* ── 상태 라벨 ── */

const STATUS_LABELS: Record<ProjectStatus, string> = {
  active: "진행 중",
  completed: "완료",
  archived: "보관",
};

const STATUS_BG: Record<ProjectStatus, string> = {
  active: "var(--accent-subtle)",
  completed: "rgba(52,211,153,0.1)",
  archived: "rgba(156,163,175,0.1)",
};

const STATUS_COLOR: Record<ProjectStatus, string> = {
  active: "var(--accent)",
  completed: "var(--success)",
  archived: "var(--text-muted)",
};

/* ── 날짜 오버듀 확인 ── */

function isOverdue(dateStr: string | null): boolean {
  if (!dateStr) return false;
  const d = new Date(dateStr);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return d < today;
}

/* ── 로딩 스켈레톤 ── */

function DashboardSkeleton() {
  return (
    <div className="p-6 animate-pulse space-y-6">
      <div className="h-8 rounded w-1/3" style={{ background: "var(--surface-active)" }} />
      <div className="h-4 rounded w-2/3" style={{ background: "var(--surface-active)" }} />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-20 rounded-lg" style={{ background: "var(--surface-active)" }} />
          ))}
        </div>
        <div className="space-y-2">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-12 rounded-lg" style={{ background: "var(--surface-active)" }} />
          ))}
        </div>
      </div>
    </div>
  );
}

/* ── 컴포넌트 ── */

interface ProjectDashboardProps {
  projectId: string;
}

export function ProjectDashboard({ projectId }: ProjectDashboardProps) {
  const activeWorkspaceId = useWorkspaceStore((s) => s.activeWorkspaceId);
  const wid = activeWorkspaceId ?? undefined;

  const { data: project, isLoading: projectLoading, error: projectError } = useProject(wid, projectId);

  /* 액션 아이템: projectId 필터 지원 */
  const { data: actionsData, isLoading: actionsLoading } = useActionItems(wid, {
    projectId,
    page: 1,
    pageSize: 20,
  });

  /* 회의 목록: projectId 필터 미지원 → 전체 fetch 후 클라이언트 필터 */
  const { data: meetingsData, isLoading: meetingsLoading } = useMeetings(wid);

  /* 노트 목록: projectId 필터 지원 */
  const { data: notesData, isLoading: notesLoading } = useNotes(wid, projectId);

  const updateAction = useUpdateActionItem(wid);

  /* 로딩 */
  if (projectLoading) return <DashboardSkeleton />;

  /* 에러 */
  if (projectError || !project) {
    return (
      <div className="p-6 flex flex-col items-center justify-center py-20 text-center">
        <span className="text-4xl mb-4">⚠️</span>
        <p className="text-sm" style={{ color: "var(--error)" }}>
          프로젝트 데이터를 불러올 수 없습니다.
        </p>
      </div>
    );
  }

  const actions = actionsData?.items ?? [];

  /* 회의: projectId 기준 클라이언트 필터 */
  /* Meeting 타입엔 projectId 필드 없음 — BE API가 projectId 필터 미지원이므로 전체 목록 상위 5개 표시 */
  const projectMeetings = (meetingsData?.items ?? []).slice(0, 5);

  const notes = notesData?.items ?? [];

  /* 최근 아이템: 회의 + 노트 합쳐 날짜순 정렬, 5개 */
  type RecentItem =
    | { kind: "meeting"; data: Meeting }
    | { kind: "note"; data: Note };

  const recentItems: RecentItem[] = [
    ...projectMeetings.map((m): RecentItem => ({ kind: "meeting", data: m })),
    ...notes.slice(0, 5).map((n): RecentItem => ({ kind: "note", data: n })),
  ]
    .sort((a, b) => {
      const aDate = a.kind === "meeting"
        ? (a.data.recordedAt ?? a.data.createdAt)
        : a.data.createdAt;
      const bDate = b.kind === "meeting"
        ? (b.data.recordedAt ?? b.data.createdAt)
        : b.data.createdAt;
      return new Date(bDate).getTime() - new Date(aDate).getTime();
    })
    .slice(0, 5);

  const isContentLoading = actionsLoading || meetingsLoading || notesLoading;

  /* 콘텐츠 3개 미만이면 온보딩 뷰 */
  const hasContent = !isContentLoading && recentItems.length >= 3;

  function handleToggleAction(action: ActionItem) {
    const nextStatus: ActionStatus =
      action.status === "done" ? "todo" : "done";
    updateAction.mutate({ id: action.id, data: { status: nextStatus } });
  }

  if (!isContentLoading && !hasContent && recentItems.length < 3) {
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

      {/* 프로액티브 인사이트 — BE 미지원, 섹션 숨김 */}
      {/* project 응답에 insight 필드가 추가되면 여기서 렌더링 */}

      {/* 로딩 중이면 스켈레톤 */}
      {isContentLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 animate-pulse">
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-20 rounded-lg" style={{ background: "var(--surface-active)" }} />
            ))}
          </div>
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-12 rounded-lg" style={{ background: "var(--surface-active)" }} />
            ))}
          </div>
        </div>
      ) : (
        /* 2컬럼 그리드 */
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* 좌: 최근 회의/노트 */}
          <div className="space-y-3">
            <h2
              className="text-sm font-semibold mb-1"
              style={{ color: "var(--text-secondary)", fontFamily: "var(--font-display)" }}
            >
              최근 회의 &middot; 노트
            </h2>
            {recentItems.length === 0 ? (
              <p className="text-xs py-4" style={{ color: "var(--text-muted)" }}>
                최근 항목이 없습니다
              </p>
            ) : (
              recentItems.map((item) =>
                item.kind === "meeting" ? (
                  <MeetingCard key={`m-${item.data.id}`} meeting={item.data} />
                ) : (
                  <NoteCard key={`n-${item.data.id}`} note={item.data} />
                )
              )
            )}
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
            </div>
            {actions.length === 0 ? (
              <p className="text-xs py-4" style={{ color: "var(--text-muted)" }}>
                액션 아이템이 없습니다
              </p>
            ) : (
              <div className="space-y-2">
                {actions.map((action) => (
                  <ActionRow
                    key={action.id}
                    action={action}
                    onToggle={() => handleToggleAction(action)}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/* ── 서브 컴포넌트 ── */

function DashboardHeader({ project }: { project: Project }) {
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
            background: STATUS_BG[project.status],
            color: STATUS_COLOR[project.status],
          }}
        >
          {STATUS_LABELS[project.status]}
        </span>
      </div>
      {project.description && (
        <p className="text-sm mb-3" style={{ color: "var(--text-secondary)" }}>
          {project.description}
        </p>
      )}
      {project.tags.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {project.tags.map((tag) => (
            <span
              key={tag}
              className="px-1.5 py-0.5 rounded text-[10px]"
              style={{
                background: "var(--surface-active)",
                color: "var(--text-muted)",
              }}
            >
              {tag}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function MeetingCard({ meeting }: { meeting: Meeting }) {
  const displayDate = meeting.recordedAt
    ? new Date(meeting.recordedAt).toLocaleDateString("ko-KR")
    : new Date(meeting.createdAt).toLocaleDateString("ko-KR");

  return (
    <Link
      href={`/meetings/${meeting.id}`}
      className="block p-4 rounded-lg border transition-colors"
      style={{
        background: "var(--surface)",
        borderColor: "var(--border-subtle)",
        borderRadius: "var(--radius-lg)",
      }}
    >
      <div className="flex items-start gap-3">
        <span className="text-base shrink-0 mt-0.5">🎙️</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-sm font-semibold truncate" style={{ color: "var(--text-primary)" }}>
              {meeting.title}
            </h3>
            <span
              className="shrink-0 px-1.5 py-0.5 rounded-full text-[10px]"
              style={{
                background: "var(--surface-active)",
                color: "var(--text-muted)",
              }}
            >
              회의
            </span>
          </div>
          <div className="text-[10px]" style={{ color: "var(--text-muted)" }}>
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

function NoteCard({ note }: { note: Note }) {
  const displayDate = new Date(note.createdAt).toLocaleDateString("ko-KR");

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
        <span className="text-base shrink-0 mt-0.5">📝</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-sm font-semibold truncate" style={{ color: "var(--text-primary)" }}>
              {note.title}
            </h3>
            <span
              className="shrink-0 px-1.5 py-0.5 rounded-full text-[10px]"
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
          <div className="text-[10px]" style={{ color: "var(--text-muted)" }}>
            {displayDate}
          </div>
        </div>
      </div>
    </Link>
  );
}

function ActionRow({ action, onToggle }: { action: ActionItem; onToggle: () => void }) {
  const isDone = action.status === "done";

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
        checked={isDone}
        onChange={onToggle}
        className="shrink-0 w-4 h-4 rounded accent-current"
        style={{ accentColor: "var(--accent)", cursor: "pointer", minHeight: "44px", minWidth: "16px" }}
      />
      <div className="flex-1 min-w-0">
        <p
          className="text-sm truncate"
          style={{
            color: isDone ? "var(--text-muted)" : "var(--text-primary)",
            textDecoration: isDone ? "line-through" : "none",
          }}
        >
          {action.title}
        </p>
        <div className="flex items-center gap-2 text-[10px]" style={{ color: "var(--text-muted)" }}>
          {action.assignee && <span>{action.assignee.displayName}</span>}
          {action.dueDate && (
            <>
              <span>&middot;</span>
              <span
                style={{
                  color: isOverdue(action.dueDate) && !isDone ? "var(--error)" : "var(--text-muted)",
                }}
              >
                {action.dueDate}
              </span>
            </>
          )}
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
