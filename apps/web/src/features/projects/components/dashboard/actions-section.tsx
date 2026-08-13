// 대시보드 우측 '이번 주 액션' 섹션 — 액션 조회/토글 mutation 소유 (BL-AV-1 분해)
"use client";

import { useActionItems, useUpdateActionItem } from "@/features/actions/hooks";
import type { ActionItem, ActionStatus } from "@/features/actions/types";

/* ── 날짜 오버듀 확인 ── */

function isOverdue(dateStr: string | null): boolean {
  if (!dateStr) return false;
  const d = new Date(dateStr);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return d < today;
}

export function ActionsSection({
  wid,
  projectId,
}: {
  wid: string | undefined;
  projectId: string;
}) {
  /* 액션 아이템: projectId 필터 지원 — dashboard-content 의 로딩 게이트와 같은
     queryKey(actionKeys.list) 라 React Query 캐시가 공유되어 중복 fetch 없음. */
  const { data: actionsData } = useActionItems(wid, {
    projectId,
    page: 1,
    pageSize: 20,
  });
  const updateAction = useUpdateActionItem(wid);

  const actions = actionsData?.items ?? [];

  function handleToggleAction(action: ActionItem) {
    const nextStatus: ActionStatus =
      action.status === "done" ? "todo" : "done";
    updateAction.mutate({ id: action.id, data: { status: nextStatus } });
  }

  return (
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
        <div className="flex items-center gap-2 text-micro" style={{ color: "var(--text-muted)" }}>
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
