"use client";

import { useState, useMemo } from "react";
import {
  DndContext,
  DragOverlay,
  closestCorners,
  PointerSensor,
  useSensor,
  useSensors,
  useDroppable,
  useDraggable,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { useActionItems, useUpdateActionItem } from "../hooks";
import { useWorkspaceStore } from "@/features/workspaces/store";
import { EmptyState } from "@/components/empty-state";
import type { ActionItem, ActionPriority } from "../types";

// --- 상수 ---

const COLUMNS = [
  { id: "todo" as const, label: "할 일", color: "var(--info)" },
  { id: "in_progress" as const, label: "진행 중", color: "var(--accent)" },
  { id: "done" as const, label: "완료", color: "var(--success)" },
];

type ColumnId = (typeof COLUMNS)[number]["id"];

const PRIORITY_COLORS: Record<ActionPriority, string> = {
  high: "var(--error)",
  medium: "var(--warning)",
  low: "var(--info)",
};

const PRIORITY_LABELS: Record<ActionPriority, string> = {
  high: "높음",
  medium: "보통",
  low: "낮음",
};

const PRIORITY_OPTIONS: { value: ActionPriority | "all"; label: string }[] = [
  { value: "all", label: "전체 우선순위" },
  { value: "high", label: "높음" },
  { value: "medium", label: "보통" },
  { value: "low", label: "낮음" },
];

// --- 메인 컴포넌트 ---

export function ActionKanban() {
  const wid = useWorkspaceStore((s) => s.activeWorkspaceId);
  const { data, isLoading, error } = useActionItems(wid ?? undefined);
  const updateAction = useUpdateActionItem(wid ?? undefined);

  const [activeId, setActiveId] = useState<string | null>(null);
  const [priorityFilter, setPriorityFilter] = useState<ActionPriority | "all">("all");

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 8 },
    })
  );

  const allItems: ActionItem[] = data?.items ?? [];

  // 우선순위 필터 적용
  const filteredItems = useMemo(() => {
    if (priorityFilter === "all") return allItems;
    return allItems.filter((item) => item.priority === priorityFilter);
  }, [allItems, priorityFilter]);

  // 컬럼별 그룹핑
  const grouped = useMemo(() => {
    const map: Record<ColumnId, ActionItem[]> = {
      todo: [],
      in_progress: [],
      done: [],
    };
    for (const item of filteredItems) {
      // cancelled 상태는 칸반에서 제외
      if (item.status === "cancelled") continue;
      const col = item.status as ColumnId;
      if (map[col]) {
        map[col].push(item);
      }
    }
    return map;
  }, [filteredItems]);

  // 드래그 중인 아이템
  const activeItem = useMemo(
    () => (activeId ? allItems.find((item) => item.id === activeId) ?? null : null),
    [activeId, allItems]
  );

  function handleDragStart(event: DragStartEvent) {
    setActiveId(String(event.active.id));
  }

  function handleDragEnd(event: DragEndEvent) {
    setActiveId(null);
    const { active, over } = event;
    if (!over) return;

    const itemId = String(active.id);
    const newStatus = String(over.id) as ColumnId;

    // 유효한 컬럼인지 확인
    if (!COLUMNS.some((col) => col.id === newStatus)) return;

    // 이미 같은 컬럼이면 무시
    const item = allItems.find((i) => i.id === itemId);
    if (!item || item.status === newStatus) return;

    // 낙관적 업데이트: mutate 호출
    updateAction.mutate({ id: itemId, data: { status: newStatus } });
  }

  // --- 렌더링 ---

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <span className="text-sm" style={{ color: "var(--text-muted)" }}>
          불러오는 중...
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

  if (allItems.length === 0) {
    return (
      <EmptyState
        icon="📋"
        title="액션 아이템이 없습니다"
        description="회의에서 추출된 액션 아이템이 칸반 보드에 표시됩니다"
      />
    );
  }

  return (
    <div>
      {/* 필터 바 */}
      <div className="flex items-center gap-3 mb-4">
        <select
          value={priorityFilter}
          onChange={(e) => setPriorityFilter(e.target.value as ActionPriority | "all")}
          className="text-xs px-2 py-1.5 rounded border"
          style={{
            background: "var(--surface)",
            borderColor: "var(--border-subtle)",
            color: "var(--text-secondary)",
            borderRadius: "var(--radius-sm)",
          }}
        >
          {PRIORITY_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* 칸반 보드 */}
      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        <div className="grid grid-cols-3 gap-4">
          {COLUMNS.map((column) => (
            <KanbanColumn
              key={column.id}
              id={column.id}
              label={column.label}
              color={column.color}
              items={grouped[column.id]}
            />
          ))}
        </div>

        <DragOverlay>
          {activeItem ? <KanbanCardOverlay item={activeItem} /> : null}
        </DragOverlay>
      </DndContext>
    </div>
  );
}

// --- KanbanColumn ---

interface KanbanColumnProps {
  id: ColumnId;
  label: string;
  color: string;
  items: ActionItem[];
}

function KanbanColumn({ id, label, color, items }: KanbanColumnProps) {
  const { setNodeRef, isOver } = useDroppable({ id });

  return (
    <div
      ref={setNodeRef}
      className="min-h-[200px] rounded-lg p-3 transition-colors"
      style={{
        background: isOver ? "var(--surface-active)" : "var(--surface-hover)",
        borderRadius: "var(--radius-lg)",
      }}
    >
      {/* 컬럼 헤더 */}
      <div className="flex items-center gap-2 mb-3">
        <span
          className="w-2 h-2 rounded-full"
          style={{ background: color }}
        />
        <span
          className="text-xs font-medium"
          style={{ color: "var(--text-secondary)" }}
        >
          {label}
        </span>
        <span
          className="text-micro px-1.5 py-0.5 rounded-full"
          style={{
            background: "var(--surface-active)",
            color: "var(--text-muted)",
            fontFamily: "var(--font-mono)",
          }}
        >
          {items.length}
        </span>
      </div>

      {/* 카드 목록 */}
      <div className="space-y-2">
        {items.map((item) => (
          <KanbanCard key={item.id} item={item} />
        ))}
      </div>
    </div>
  );
}

// --- KanbanCardContent (순수 view) — KanbanCard + DragOverlay 양쪽에서 재사용 ---

function KanbanCardContent({ item }: { item: ActionItem }) {
  return (
    <>
      {/* 우선순위 인디케이터 + 제목 */}
      <div className="flex items-start gap-2 mb-2">
        <span
          className="w-1.5 h-1.5 rounded-full mt-1.5 shrink-0"
          style={{ background: PRIORITY_COLORS[item.priority] }}
        />
        <p className="text-sm flex-1" style={{ color: "var(--text-primary)" }}>
          {item.title}
        </p>
      </div>

      {/* 메타 정보 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {item.assignee && (
            <span
              className="text-micro px-1.5 py-0.5 rounded-full"
              style={{
                background: "var(--surface-active)",
                color: "var(--text-muted)",
              }}
            >
              {item.assignee.displayName}
            </span>
          )}
          {/* 우선순위 뱃지 */}
          <span
            className="text-micro px-1.5 py-0.5 rounded-full"
            style={{
              background: `${PRIORITY_COLORS[item.priority]}20`,
              color: PRIORITY_COLORS[item.priority],
            }}
          >
            {PRIORITY_LABELS[item.priority]}
          </span>
        </div>
        {item.dueDate && (
          <span
            className="text-micro"
            style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}
          >
            {item.dueDate}
          </span>
        )}
      </div>
    </>
  );
}

// --- KanbanCard (드래그 가능) ---

function KanbanCard({ item }: { item: ActionItem }) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: item.id,
  });

  return (
    <div
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      className="p-3 rounded border cursor-grab active:cursor-grabbing transition-opacity"
      style={{
        background: "var(--surface)",
        borderColor: "var(--border-subtle)",
        borderRadius: "var(--radius-md)",
        opacity: isDragging ? 0.4 : 1,
      }}
    >
      <KanbanCardContent item={item} />
    </div>
  );
}

// --- DragOverlay용 카드 (드래그 중 미리보기, shadow + 고정 width) ---

function KanbanCardOverlay({ item }: { item: ActionItem }) {
  return (
    <div
      className="p-3 rounded border shadow-lg"
      style={{
        background: "var(--surface)",
        borderColor: "var(--border-subtle)",
        borderRadius: "var(--radius-md)",
        width: 280,
      }}
    >
      <KanbanCardContent item={item} />
    </div>
  );
}
