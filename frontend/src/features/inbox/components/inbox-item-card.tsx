"use client";

import type { InboxItem } from "../types";

interface InboxItemCardProps {
  item: InboxItem;
  onClassify?: (item: InboxItem) => void;
  onDismiss?: (item: InboxItem) => void;
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

export function InboxItemCard({ item, onClassify, onDismiss }: InboxItemCardProps) {
  return (
    <div
      className="p-4 rounded border transition-colors"
      style={{
        background: "var(--surface)",
        borderColor: "var(--border-subtle)",
        borderRadius: "var(--radius-md)",
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

      {/* AI 추천 */}
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
      <div className="flex items-center gap-2">
        <button
          onClick={() => onClassify?.(item)}
          className="px-3 py-1.5 rounded text-xs font-medium transition-colors"
          style={{
            background: "var(--accent)",
            color: "var(--background)",
            borderRadius: "var(--radius-sm)",
          }}
        >
          분류 확정
        </button>
        <button
          onClick={() => onDismiss?.(item)}
          className="px-3 py-1.5 rounded text-xs font-medium transition-colors border"
          style={{
            borderColor: "var(--border)",
            color: "var(--text-muted)",
            borderRadius: "var(--radius-sm)",
          }}
        >
          무시
        </button>
      </div>
    </div>
  );
}
