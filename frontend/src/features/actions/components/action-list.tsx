"use client";

import type { ActionItem } from "../types";
import { useActionItems } from "../hooks";
import { useWorkspaceStore } from "@/features/workspaces/store";
import { EmptyState } from "@/components/empty-state";

const PRIORITY_COLORS: Record<string, string> = {
  high: "var(--error)",
  medium: "var(--warning)",
  low: "var(--info)",
};

const PRIORITY_LABELS: Record<string, string> = {
  high: "높음",
  medium: "보통",
  low: "낮음",
};

const STATUS_LABELS: Record<string, string> = {
  todo: "할 일",
  in_progress: "진행 중",
  done: "완료",
  cancelled: "취소",
};

export function ActionList() {
  const wid = useWorkspaceStore((s) => s.activeWorkspaceId);
  const { data, isLoading, error } = useActionItems(wid ?? undefined);

  const items: ActionItem[] = data?.items ?? [];

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <span className="text-sm" style={{ color: "var(--text-muted)" }}>
          로딩 중...
        </span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-12">
        <span className="text-sm" style={{ color: "var(--error)" }}>
          액션 아이템을 불러오지 못했습니다
        </span>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <EmptyState
        icon="✅"
        title="액션 아이템이 없습니다"
        description="회의에서 추출된 액션 아이템이 여기에 표시됩니다"
      />
    );
  }

  return (
    <div className="space-y-2">
      {items.map((item) => (
        <div
          key={item.id}
          className="flex items-center gap-4 p-3 rounded border"
          style={{
            background: "var(--surface)",
            borderColor: "var(--border-subtle)",
            borderRadius: "var(--radius-md)",
          }}
        >
          {/* 우선순위 */}
          <span
            className="w-2 h-2 rounded-full shrink-0"
            style={{ background: PRIORITY_COLORS[item.priority] }}
          />

          {/* 제목 */}
          <span className="flex-1 text-sm truncate" style={{ color: "var(--text-primary)" }}>
            {item.title}
          </span>

          {/* 담당자 */}
          {item.assignee && (
            <span className="text-xs" style={{ color: "var(--text-muted)" }}>
              {item.assignee.displayName}
            </span>
          )}

          {/* 마감일 */}
          {item.dueDate && (
            <span
              className="text-xs"
              style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}
            >
              {item.dueDate}
            </span>
          )}

          {/* 상태 뱃지 */}
          <span
            className="px-2 py-0.5 rounded-full text-[10px]"
            style={{
              background: "var(--surface-active)",
              color: "var(--text-muted)",
            }}
          >
            {STATUS_LABELS[item.status]}
          </span>

          {/* 우선순위 뱃지 */}
          <span
            className="px-2 py-0.5 rounded-full text-[10px]"
            style={{
              background: `${PRIORITY_COLORS[item.priority]}20`,
              color: PRIORITY_COLORS[item.priority],
            }}
          >
            {PRIORITY_LABELS[item.priority]}
          </span>
        </div>
      ))}
    </div>
  );
}
