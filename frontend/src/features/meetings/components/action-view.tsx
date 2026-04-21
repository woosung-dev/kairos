"use client";

import { useActionItems, useUpdateActionItem } from "@/features/actions/hooks";
import { useWorkspaceStore } from "@/features/workspaces/store";
import type { ActionItem, ActionStatus } from "@/features/actions/types";

/* ── Props ── */

interface ActionViewProps {
  meetingId: string;
}

/* ── 날짜 오버듀 확인 ── */

function isOverdue(dateStr: string | null): boolean {
  if (!dateStr) return false;
  const dueDate = new Date(dateStr);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return dueDate < today;
}

/* ── 컴포넌트 ── */

export function ActionView({ meetingId }: ActionViewProps) {
  const activeWorkspaceId = useWorkspaceStore((s) => s.activeWorkspaceId);
  const wid = activeWorkspaceId ?? undefined;

  /* meetingId 필터로 해당 회의의 액션만 조회 */
  const { data, isLoading, error } = useActionItems(wid, { page: 1, pageSize: 100 });
  const updateAction = useUpdateActionItem(wid);

  /* 클라이언트 사이드 meetingId 필터 (BE fetchActionItems는 meetingId 필터 미지원) */
  const actions = data?.items.filter((a) => a.meetingId === meetingId) ?? [];

  function handleToggle(action: ActionItem) {
    const nextStatus: ActionStatus =
      action.status === "done" ? "todo" : "done";
    updateAction.mutate({ id: action.id, data: { status: nextStatus } });
  }

  /* 로딩 */
  if (isLoading) {
    return (
      <div className="space-y-2 animate-pulse">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="h-14 rounded-lg"
            style={{ background: "var(--surface-active)" }}
          />
        ))}
      </div>
    );
  }

  /* 에러 */
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <p className="text-sm" style={{ color: "var(--error)" }}>
          액션 아이템을 불러올 수 없습니다.
        </p>
      </div>
    );
  }

  /* 빈 상태 */
  if (actions.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <span className="text-4xl mb-4">✅</span>
        <h3
          className="text-lg font-semibold mb-2"
          style={{ color: "var(--text-primary)", fontFamily: "var(--font-display)" }}
        >
          액션 아이템이 없습니다
        </h3>
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          AI 분석이 완료되면 액션 아이템이 자동으로 추출됩니다
        </p>
      </div>
    );
  }

  const doneCount = actions.filter((a) => a.status === "done").length;
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
            onToggle={() => handleToggle(action)}
          />
        ))}
      </div>
    </div>
  );
}

/* ── 서브 컴포넌트 ── */

function ActionRow({ action, onToggle }: { action: ActionItem; onToggle: () => void }) {
  const isDone = action.status === "done";

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
        checked={isDone}
        onChange={onToggle}
        className="shrink-0 w-4 h-4 mt-0.5 rounded accent-current"
        style={{ accentColor: "var(--accent)", cursor: "pointer" }}
      />

      {/* 내용 */}
      <div className="flex-1 min-w-0">
        <p
          className="text-sm"
          style={{
            color: isDone ? "var(--text-muted)" : "var(--text-primary)",
            textDecoration: isDone ? "line-through" : "none",
          }}
        >
          {action.title}
        </p>
        <div className="flex items-center gap-3 mt-1">
          {action.assignee && (
            <span className="text-[11px]" style={{ color: "var(--text-muted)" }}>
              {action.assignee.displayName}
            </span>
          )}
          {action.dueDate && (
            <>
              <span className="text-[11px]" style={{ color: "var(--text-muted)" }}>&middot;</span>
              <span
                className="text-[11px]"
                style={{
                  color: isOverdue(action.dueDate) && !isDone ? "var(--error)" : "var(--text-muted)",
                  fontFamily: "var(--font-mono)",
                }}
              >
                {action.dueDate}
              </span>
            </>
          )}
          {/* 우선순위 뱃지 */}
          {action.priority === "high" && (
            <span
              className="text-[10px] ml-auto px-1.5 py-0.5 rounded"
              style={{
                background: "rgba(239,68,68,0.1)",
                color: "var(--error)",
              }}
            >
              높음
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
