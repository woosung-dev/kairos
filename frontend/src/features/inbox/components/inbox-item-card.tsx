"use client";

import { useState } from "react";
import type { InboxItem } from "../types";
import { useClassifyInbox, useDismissInbox } from "../hooks";
import { useWorkspaceStore } from "@/features/workspaces/store";
import { ProjectCombobox } from "@/features/projects/components/project-combobox";

interface InboxItemCardProps {
  item: InboxItem;
}

const SOURCE_LABELS: Record<string, string> = {
  meeting: "회의",
  note: "노트",
  attachment: "자료",
};

const SOURCE_ICONS: Record<string, string> = {
  meeting: "🎙️",
  note: "📝",
  attachment: "📎",
};

export function InboxItemCard({ item }: InboxItemCardProps) {
  const [isComboboxOpen, setIsComboboxOpen] = useState(false);
  const activeWorkspaceId = useWorkspaceStore((s) => s.activeWorkspaceId);
  const classifyInbox = useClassifyInbox(activeWorkspaceId ?? undefined);
  const dismissInbox = useDismissInbox(activeWorkspaceId ?? undefined);

  const isActioning = classifyInbox.isPending || dismissInbox.isPending;

  /** AI 추천 프로젝트로 확정 */
  function handleConfirm() {
    if (!item.aiSuggestedProjectId) return;
    classifyInbox.mutate({ id: item.id, projectIds: [item.aiSuggestedProjectId] });
  }

  /** 무시 */
  function handleDismiss() {
    dismissInbox.mutate(item.id);
  }

  /** ProjectCombobox에서 선택 시 */
  function handleProjectSelect(projectId: string) {
    classifyInbox.mutate({ id: item.id, projectIds: [projectId] });
    setIsComboboxOpen(false);
  }

  return (
    <div
      className="p-4 rounded border transition-colors"
      style={{
        background: "var(--surface)",
        borderColor: "var(--border-subtle)",
        borderRadius: "var(--radius-md)",
        opacity: isActioning ? 0.6 : 1,
        pointerEvents: isActioning ? "none" : "auto",
      }}
    >
      {/* 상단: 소스 뱃지 + 제목 */}
      <div className="flex items-start gap-3 mb-2">
        <span className="text-lg shrink-0">{SOURCE_ICONS[item.sourceType]}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3
              className="text-sm font-semibold truncate"
              style={{ color: "var(--text-primary)" }}
            >
              {item.title}
            </h3>
            <span
              className="shrink-0 px-1.5 py-0.5 rounded-full text-[10px]"
              style={{
                background: "var(--surface-active)",
                color: "var(--text-muted)",
              }}
            >
              {SOURCE_LABELS[item.sourceType]}
            </span>
          </div>
          {item.summary && (
            <p className="text-xs line-clamp-2" style={{ color: "var(--text-secondary)" }}>
              {item.summary}
            </p>
          )}
        </div>
      </div>

      {/* AI 태그 */}
      {item.aiSuggestedTags.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {item.aiSuggestedTags.map((tag) => (
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

      {/* AI 추천 프로젝트 */}
      {item.aiSuggestedProjectTitle && (
        <div
          className="flex items-center gap-2 px-3 py-2 rounded mb-3"
          style={{
            background: "var(--accent-subtle)",
            borderRadius: "var(--radius-sm)",
          }}
        >
          <span className="text-xs" style={{ color: "var(--accent)" }}>
            AI 추천:
          </span>
          <span className="text-xs font-medium" style={{ color: "var(--accent)" }}>
            {item.aiSuggestedProjectTitle}
          </span>
          {item.aiConfidence !== null && (
            <span
              className="text-[10px] ml-auto"
              style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}
            >
              {Math.round(item.aiConfidence * 100)}%
            </span>
          )}
        </div>
      )}

      {/* 액션 버튼 */}
      {!item.isProcessed && (
        <div className="flex items-center gap-2 relative">
          {/* AI 추천이 있으면 확정 버튼 */}
          {item.aiSuggestedProjectId && (
            <button
              onClick={handleConfirm}
              disabled={isActioning}
              className="px-3 py-1.5 rounded text-xs font-medium transition-colors"
              style={{
                background: "var(--accent)",
                color: "var(--background)",
                borderRadius: "var(--radius-sm)",
              }}
            >
              확정
            </button>
          )}

          {/* 변경 (다른 프로젝트 선택) */}
          <button
            onClick={() => setIsComboboxOpen(!isComboboxOpen)}
            className="px-3 py-1.5 rounded text-xs font-medium transition-colors border"
            style={{
              borderColor: "var(--accent)",
              color: "var(--accent)",
              borderRadius: "var(--radius-sm)",
            }}
          >
            {item.aiSuggestedProjectId ? "변경" : "프로젝트 선택"}
          </button>

          {/* 무시 */}
          <button
            onClick={handleDismiss}
            disabled={isActioning}
            className="px-3 py-1.5 rounded text-xs font-medium transition-colors border"
            style={{
              borderColor: "var(--border)",
              color: "var(--text-muted)",
              borderRadius: "var(--radius-sm)",
            }}
          >
            무시
          </button>

          {/* ProjectCombobox 드롭다운 */}
          {isComboboxOpen && (
            <div className="absolute top-full left-0 mt-1">
              <ProjectCombobox
                onSelect={handleProjectSelect}
                onClose={() => setIsComboboxOpen(false)}
              />
            </div>
          )}
        </div>
      )}

      {/* 처리 완료 표시 */}
      {item.isProcessed && (
        <div className="flex items-center gap-1.5">
          <span className="text-xs" style={{ color: "var(--success)" }}>
            처리 완료
          </span>
        </div>
      )}
    </div>
  );
}
