"use client";

import type { ActionItem, ActionStatus } from "../types";
import { EmptyState } from "@/components/empty-state";

interface ActionKanbanProps {
  items?: ActionItem[];
}

const COLUMNS: { status: ActionStatus; label: string; color: string }[] = [
  { status: "todo", label: "할 일", color: "var(--info)" },
  { status: "in_progress", label: "진행 중", color: "var(--accent)" },
  { status: "done", label: "완료", color: "var(--success)" },
  { status: "cancelled", label: "취소", color: "var(--text-muted)" },
];

export function ActionKanban({ items = [] }: ActionKanbanProps) {
  if (items.length === 0) {
    return (
      <EmptyState
        icon="📋"
        title="액션 아이템이 없습니다"
        description="회의에서 추출된 액션 아이템이 칸반 보드에 표시됩니다"
      />
    );
  }

  return (
    <div className="grid grid-cols-4 gap-4">
      {COLUMNS.map((column) => {
        const columnItems = items.filter((item) => item.status === column.status);
        return (
          <div key={column.status}>
            {/* 컬럼 헤더 */}
            <div className="flex items-center gap-2 mb-3">
              <span
                className="w-2 h-2 rounded-full"
                style={{ background: column.color }}
              />
              <span
                className="text-xs font-medium"
                style={{ color: "var(--text-secondary)" }}
              >
                {column.label}
              </span>
              <span
                className="text-[10px] px-1.5 py-0.5 rounded-full"
                style={{
                  background: "var(--surface-active)",
                  color: "var(--text-muted)",
                  fontFamily: "var(--font-mono)",
                }}
              >
                {columnItems.length}
              </span>
            </div>

            {/* 카드 */}
            <div className="space-y-2">
              {columnItems.map((item) => (
                <div
                  key={item.id}
                  className="p-3 rounded border"
                  style={{
                    background: "var(--surface)",
                    borderColor: "var(--border-subtle)",
                    borderRadius: "var(--radius-md)",
                  }}
                >
                  <p className="text-sm mb-2" style={{ color: "var(--text-primary)" }}>
                    {item.title}
                  </p>
                  <div className="flex items-center justify-between">
                    {item.assignee && (
                      <span className="text-[10px]" style={{ color: "var(--text-muted)" }}>
                        {item.assignee.displayName}
                      </span>
                    )}
                    {item.dueDate && (
                      <span
                        className="text-[10px]"
                        style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}
                      >
                        {item.dueDate}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
