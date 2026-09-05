"use client";

// 워크스페이스 전체 액션 보드 (/actions) — 회의에서 추출된 액션 + 직접 추가한 액션 통합 뷰.
//
// ★한 번에 전부 가져와 클라이언트에서 필터한다 — BE status 필터는 단일 값이라
//   상태별 카운트(할 일/진행 중/완료)를 한 번에 낼 수 없고, 프로젝트 미배정(projectId=null)·
//   "내 액션만" 도 BE 필터가 없다. 액션은 워크스페이스당 수십 건 규모라 pageSize=100 으로 충분하다.

import { useMemo, useState } from "react";
import Link from "next/link";
import { CheckCircle2, Mic } from "lucide-react";
import { toast } from "sonner";
import { useActionItems, useAssigneeNames, useUpdateActionItem } from "../hooks";
import type { ActionItem, ActionStatus } from "../types";
import { useProjects } from "@/features/projects/hooks";
import { useMe } from "@/features/auth/hooks";
import { useWorkspaceStore } from "@/features/workspaces/store";
import { EmptyState } from "@/components/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDate, isOverdue } from "@/lib/format-date";

/* ── 필터 정의 ── */

/** "전체" 는 cancelled 를 제외한다 — 취소된 액션은 보드에서 노이즈. */
type StatusFilter = "all" | Exclude<ActionStatus, "cancelled">;

const STATUS_FILTERS: ReadonlyArray<{ value: StatusFilter; label: string }> = [
  { value: "all", label: "전체" },
  { value: "todo", label: "할 일" },
  { value: "in_progress", label: "진행 중" },
  { value: "done", label: "완료" },
];

/** 프로젝트 select 의 "미배정" 옵션 값 — 실제 UUID 와 충돌하지 않는 sentinel. */
const UNASSIGNED_PROJECT = "__unassigned__";

/* ── 정렬 ── */

function toTime(iso: string): number {
  const t = new Date(iso).getTime();
  return Number.isNaN(t) ? 0 : t;
}

/**
 * 미완료 우선 → (미완료 안에서) 지연 우선 → 마감일 빠른 순 → 최신 생성 순.
 * 완료는 맨 아래, 최근 갱신 순.
 */
function compareActions(a: ActionItem, b: ActionItem): number {
  const isADone = a.status === "done";
  const isBDone = b.status === "done";
  if (isADone !== isBDone) return isADone ? 1 : -1;
  if (isADone) return toTime(b.updatedAt) - toTime(a.updatedAt);

  const isAOverdue = isOverdue(a.dueDate);
  const isBOverdue = isOverdue(b.dueDate);
  if (isAOverdue !== isBOverdue) return isAOverdue ? -1 : 1;

  if (a.dueDate !== b.dueDate) {
    if (!a.dueDate) return 1;
    if (!b.dueDate) return -1;
    return a.dueDate.localeCompare(b.dueDate);
  }
  return toTime(b.createdAt) - toTime(a.createdAt);
}

/* ── 컴포넌트 ── */

export function ActionBoard() {
  const activeWorkspaceId = useWorkspaceStore((s) => s.activeWorkspaceId);
  const hasRole = useWorkspaceStore((s) => s.hasRole);
  const wid = activeWorkspaceId ?? undefined;
  const canWrite = hasRole("member");

  const { data, isLoading, error } = useActionItems(wid, { page: 1, pageSize: 100 });
  const { data: projectsPage } = useProjects(wid, { status: "active" });
  const { data: me } = useMe();
  const updateAction = useUpdateActionItem(wid);
  const assigneeNames = useAssigneeNames(wid);

  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [projectFilter, setProjectFilter] = useState("");
  const [isMineOnly, setIsMineOnly] = useState(false);

  const allActions = useMemo(() => data?.items ?? [], [data]);
  const projects = useMemo(() => projectsPage?.items ?? [], [projectsPage]);

  const projectTitleMap = useMemo(() => {
    const map = new Map<string, string>();
    projects.forEach((p) => map.set(p.id, p.title));
    return map;
  }, [projects]);

  const counts = useMemo(
    () => ({
      todo: allActions.filter((a) => a.status === "todo").length,
      inProgress: allActions.filter((a) => a.status === "in_progress").length,
      done: allActions.filter((a) => a.status === "done").length,
    }),
    [allActions],
  );

  const visibleActions = useMemo(() => {
    const meId = me?.id;
    return allActions
      .filter((a) =>
        statusFilter === "all" ? a.status !== "cancelled" : a.status === statusFilter,
      )
      .filter((a) => {
        if (!projectFilter) return true;
        if (projectFilter === UNASSIGNED_PROJECT) return a.projectId === null;
        return a.projectId === projectFilter;
      })
      .filter((a) => (isMineOnly && meId ? a.assigneeId === meId : true))
      .sort(compareActions);
  }, [allActions, statusFilter, projectFilter, isMineOnly, me?.id]);

  function handleToggle(action: ActionItem) {
    const nextStatus: ActionStatus = action.status === "done" ? "todo" : "done";
    updateAction.mutate(
      { id: action.id, data: { status: nextStatus } },
      { onError: () => toast.error("액션 상태 변경에 실패했습니다") },
    );
  }

  return (
    <div className="p-6" data-testid="action-board">
      {/* 헤더 */}
      <div className="mb-6">
        <h1
          className="text-2xl font-bold mb-1"
          style={{ fontFamily: "var(--font-display)", color: "var(--text-primary)" }}
        >
          액션
        </h1>
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          회의에서 추출된 액션과 직접 추가한 액션을 한곳에서 관리합니다
        </p>
        {data && (
          <p
            className="text-caption mt-2"
            style={{ fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}
          >
            할 일 {counts.todo} · 진행 중 {counts.inProgress} · 완료 {counts.done}
          </p>
        )}
      </div>

      {!wid ? (
        <p className="py-16 text-center text-sm" style={{ color: "var(--text-muted)" }}>
          워크스페이스를 선택해주세요
        </p>
      ) : isLoading ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-14 rounded-lg" />
          ))}
        </div>
      ) : error ? (
        <p className="py-16 text-center text-sm" style={{ color: "var(--error)" }}>
          액션을 불러올 수 없습니다
        </p>
      ) : (
        <>
          {/* 필터 */}
          <div className="flex flex-wrap items-center gap-2 mb-4">
            {STATUS_FILTERS.map((f) => (
              <FilterPill
                key={f.value}
                isActive={statusFilter === f.value}
                onClick={() => setStatusFilter(f.value)}
                data-testid={`action-status-filter-${f.value}`}
              >
                {f.label}
              </FilterPill>
            ))}

            <select
              aria-label="프로젝트 필터"
              value={projectFilter}
              onChange={(e) => setProjectFilter(e.target.value)}
              className="min-h-8 max-w-full px-2 py-1 rounded text-xs bg-transparent border outline-none"
              style={{
                borderColor: "var(--border)",
                color: "var(--text-secondary)",
                borderRadius: "var(--radius-sm)",
                cursor: "pointer",
              }}
            >
              <option value="">모든 프로젝트</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.title}
                </option>
              ))}
              <option value={UNASSIGNED_PROJECT}>프로젝트 미배정</option>
            </select>

            {me && (
              <FilterPill
                isActive={isMineOnly}
                onClick={() => setIsMineOnly((v) => !v)}
                aria-pressed={isMineOnly}
                data-testid="action-mine-filter"
              >
                내 액션만
              </FilterPill>
            )}
          </div>

          {/* 목록 */}
          {visibleActions.length === 0 ? (
            allActions.length > 0 ? (
              <EmptyState
                icon={<CheckCircle2 className="w-10 h-10" />}
                title="액션 아이템이 없습니다"
                description="회의를 분석하면 액션이 자동으로 추출됩니다. 필터를 바꿔보세요."
              />
            ) : (
              <EmptyState
                icon={<CheckCircle2 className="w-10 h-10" />}
                title="액션 아이템이 없습니다"
                description="회의를 텍스트나 음성으로 추가하면 AI가 액션을 추출합니다."
                action={{ label: "회의 추가", href: "/new" }}
              />
            )
          ) : (
            <div className="space-y-2">
              {visibleActions.map((action) => (
                <ActionRow
                  key={action.id}
                  action={action}
                  projectTitle={
                    action.projectId ? projectTitleMap.get(action.projectId) ?? null : null
                  }
                  assigneeName={
                    action.assigneeId ? assigneeNames.get(action.assigneeId) : undefined
                  }
                  canWrite={canWrite}
                  isPending={updateAction.isPending && updateAction.variables?.id === action.id}
                  onToggle={() => handleToggle(action)}
                />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

/* ── 서브 컴포넌트 ── */

function FilterPill({
  isActive,
  children,
  ...rest
}: { isActive: boolean } & React.ComponentProps<"button">) {
  return (
    <button
      type="button"
      className="min-h-8 px-3 py-1 rounded-full text-caption font-medium transition-colors cursor-pointer"
      style={{
        background: isActive ? "var(--accent-subtle)" : "transparent",
        color: isActive ? "var(--accent)" : "var(--text-muted)",
        border: isActive ? "1px solid var(--accent)" : "1px solid var(--border-subtle)",
      }}
      {...rest}
    >
      {children}
    </button>
  );
}

function ActionRow({
  action,
  projectTitle,
  assigneeName,
  canWrite,
  isPending,
  onToggle,
}: {
  action: ActionItem;
  projectTitle: string | null;
  assigneeName?: string;
  canWrite: boolean;
  isPending: boolean;
  onToggle: () => void;
}) {
  const isDone = action.status === "done";
  const isLate = isOverdue(action.dueDate) && !isDone;

  return (
    <div
      className="flex items-start gap-3 px-3 py-2 rounded-lg border transition-colors"
      style={{
        background: "var(--surface)",
        borderColor: "var(--border-subtle)",
        borderRadius: "var(--radius-lg)",
      }}
      data-testid="action-row"
    >
      <input
        type="checkbox"
        checked={isDone}
        onChange={onToggle}
        disabled={!canWrite || isPending}
        aria-label={`${action.title} 완료 토글`}
        title={canWrite ? undefined : "Member 이상만 변경할 수 있습니다"}
        className="shrink-0 w-4 h-4 rounded accent-current"
        style={{
          accentColor: "var(--accent)",
          cursor: canWrite ? "pointer" : "not-allowed",
          minHeight: "32px",
          minWidth: "16px",
        }}
      />

      <div className="flex-1 min-w-0 py-1.5">
        <p
          className="text-sm break-words"
          style={{
            color: isDone ? "var(--text-muted)" : "var(--text-primary)",
            textDecoration: isDone ? "line-through" : "none",
          }}
        >
          {action.title}
        </p>
        {(assigneeName || action.dueDate || action.priority !== "medium") && (
          <div
            className="flex flex-wrap items-center gap-x-2 gap-y-0.5 mt-0.5 text-micro"
            style={{ color: "var(--text-muted)" }}
          >
            {assigneeName && <span>{assigneeName}</span>}
            {action.dueDate && (
              <>
                {assigneeName && <span>&middot;</span>}
                <span
                  style={{
                    color: isLate ? "var(--error)" : "var(--text-muted)",
                    fontFamily: "var(--font-mono)",
                  }}
                >
                  {formatDate(action.dueDate)}
                </span>
              </>
            )}
            {action.priority === "high" && (
              <span
                className="px-1.5 py-0.5 rounded"
                style={{ background: "rgba(239,68,68,0.1)", color: "var(--error)" }}
              >
                높음
              </span>
            )}
            {action.priority === "low" && (
              <span
                className="px-1.5 py-0.5 rounded"
                style={{ background: "var(--surface-active)", color: "var(--text-muted)" }}
              >
                낮음
              </span>
            )}
          </div>
        )}
      </div>

      {(action.projectId || action.meetingId) && (
        <div className="flex items-center gap-1 shrink-0 min-w-0">
          {action.projectId && (
            <Link
              href={`/projects/${action.projectId}`}
              className="inline-flex items-center min-h-8 max-w-[6rem] sm:max-w-[10rem] px-1.5 rounded text-micro truncate"
              style={{ background: "var(--accent-subtle)", color: "var(--accent)" }}
              title={projectTitle ?? undefined}
            >
              {projectTitle ?? "프로젝트"}
            </Link>
          )}
          {action.meetingId && (
            <Link
              href={`/meetings/${action.meetingId}`}
              aria-label="원본 회의 보기"
              className="inline-flex items-center justify-center w-8 h-8 rounded transition-colors hover:bg-[var(--surface-hover)]"
              style={{ color: "var(--text-muted)" }}
            >
              <Mic className="w-3.5 h-3.5" />
            </Link>
          )}
        </div>
      )}
    </div>
  );
}
