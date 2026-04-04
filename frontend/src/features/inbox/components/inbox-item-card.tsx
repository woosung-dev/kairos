"use client";

import { useState } from "react";
import type { UUID } from "@/types";

/* ── 타입 ── */

interface SmartInboxItemData {
  id: UUID;
  title: string;
  sourceType: "meeting" | "note" | "attachment";
  aiSuggestedProject: string;
  aiConfidence: number;
  aiSuggestedTags: string[];
  summary: string | null;
  isAutoProcessed: boolean;
}

interface SmartInboxItemCardProps {
  item: SmartInboxItemData;
}

/* ── 라벨/아이콘 맵 ── */

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

/* ── 컴포넌트 ── */

export function SmartInboxItemCard({ item }: SmartInboxItemCardProps) {
  const [status, setStatus] = useState<"idle" | "confirmed" | "dismissed" | "editing">("idle");

  const confidencePercent = Math.round(item.aiConfidence * 100);

  function handleConfirm() {
    setStatus("confirmed");
  }

  function handleDismiss() {
    setStatus("dismissed");
  }

  function handleEdit() {
    setStatus("editing");
  }

  function handleRevert() {
    setStatus("idle");
  }

  /* 확정/무시된 상태이면 축약 표시 */
  if (status === "confirmed") {
    return (
      <div
        className="px-4 py-3 rounded-lg border flex items-center gap-3"
        style={{
          background: "var(--surface)",
          borderColor: "var(--border-subtle)",
          borderRadius: "var(--radius-lg)",
          opacity: 0.7,
        }}
      >
        <span className="text-sm">✅</span>
        <span className="text-sm flex-1" style={{ color: "var(--text-secondary)" }}>
          {item.title} &rarr; <strong style={{ color: "var(--accent)" }}>{item.aiSuggestedProject}</strong>
        </span>
        <button
          onClick={handleRevert}
          className="text-xs px-2 py-1 rounded border transition-colors"
          style={{
            borderColor: "var(--border)",
            color: "var(--text-muted)",
            borderRadius: "var(--radius-sm)",
            cursor: "pointer",
            minHeight: "44px",
          }}
        >
          ↩ 되돌리기
        </button>
      </div>
    );
  }

  if (status === "dismissed") {
    return (
      <div
        className="px-4 py-3 rounded-lg border flex items-center gap-3"
        style={{
          background: "var(--surface)",
          borderColor: "var(--border-subtle)",
          borderRadius: "var(--radius-lg)",
          opacity: 0.5,
        }}
      >
        <span className="text-sm">🗑</span>
        <span className="text-sm flex-1 line-through" style={{ color: "var(--text-muted)" }}>
          {item.title}
        </span>
        <button
          onClick={handleRevert}
          className="text-xs px-2 py-1 rounded border transition-colors"
          style={{
            borderColor: "var(--border)",
            color: "var(--text-muted)",
            borderRadius: "var(--radius-sm)",
            cursor: "pointer",
            minHeight: "44px",
          }}
        >
          ↩ 되돌리기
        </button>
      </div>
    );
  }

  return (
    <div
      className="p-4 rounded-lg border transition-colors"
      style={{
        background: "var(--surface)",
        borderColor: "var(--border-subtle)",
        borderRadius: "var(--radius-lg)",
      }}
    >
      {/* 상단: 소스 아이콘 + 제목 */}
      <div className="flex items-start gap-3 mb-2">
        <span className="text-lg shrink-0">{SOURCE_ICONS[item.sourceType]}</span>
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
          {item.aiSuggestedProject}
        </span>
        <span
          className="text-[10px] ml-auto"
          style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}
        >
          {confidencePercent}%
        </span>
      </div>

      {/* 액션 버튼 */}
      {!item.isAutoProcessed ? (
        /* 확인 필요 아이템: 확정 / 다른 프로젝트 / 무시 */
        <div className="flex items-center gap-2">
          <button
            onClick={handleConfirm}
            className="px-3 py-1.5 rounded text-xs font-medium transition-colors"
            style={{
              background: "var(--accent)",
              color: "var(--background)",
              borderRadius: "var(--radius-sm)",
              cursor: "pointer",
              minHeight: "44px",
            }}
          >
            ✅ 확정
          </button>
          <button
            onClick={handleEdit}
            className="px-3 py-1.5 rounded text-xs font-medium transition-colors border"
            style={{
              borderColor: "var(--accent)",
              color: "var(--accent)",
              borderRadius: "var(--radius-sm)",
              cursor: "pointer",
              minHeight: "44px",
            }}
          >
            ✏️ 다른 프로젝트
          </button>
          <button
            onClick={handleDismiss}
            className="px-3 py-1.5 rounded text-xs font-medium transition-colors border"
            style={{
              borderColor: "var(--border)",
              color: "var(--text-muted)",
              borderRadius: "var(--radius-sm)",
              cursor: "pointer",
              minHeight: "44px",
            }}
          >
            🗑 무시
          </button>
        </div>
      ) : (
        /* 자동 처리된 아이템: 수정 / 되돌리기 */
        <div className="flex items-center gap-2">
          <button
            onClick={handleEdit}
            className="px-3 py-1.5 rounded text-xs font-medium transition-colors border"
            style={{
              borderColor: "var(--accent)",
              color: "var(--accent)",
              borderRadius: "var(--radius-sm)",
              cursor: "pointer",
              minHeight: "44px",
            }}
          >
            ✏️ 수정
          </button>
          <button
            onClick={handleDismiss}
            className="px-3 py-1.5 rounded text-xs font-medium transition-colors border"
            style={{
              borderColor: "var(--border)",
              color: "var(--text-muted)",
              borderRadius: "var(--radius-sm)",
              cursor: "pointer",
              minHeight: "44px",
            }}
          >
            ↩ 되돌리기
          </button>
        </div>
      )}

      {/* "다른 프로젝트" 편집 모드 (간단한 목업) */}
      {status === "editing" && (
        <div
          className="mt-3 p-3 rounded border"
          style={{
            background: "var(--surface-hover)",
            borderColor: "var(--border)",
            borderRadius: "var(--radius-sm)",
          }}
        >
          <p className="text-xs mb-2" style={{ color: "var(--text-secondary)" }}>
            프로젝트를 선택하세요 (Mock)
          </p>
          <div className="flex flex-wrap gap-2">
            {["Q2 제품 로드맵", "디자인 시스템", "DevOps 개선", "사용자 리서치"].map((proj) => (
              <button
                key={proj}
                onClick={() => setStatus("confirmed")}
                className="px-2 py-1 rounded text-xs transition-colors border"
                style={{
                  borderColor: proj === item.aiSuggestedProject ? "var(--accent)" : "var(--border)",
                  color: proj === item.aiSuggestedProject ? "var(--accent)" : "var(--text-secondary)",
                  background: proj === item.aiSuggestedProject ? "var(--accent-subtle)" : "transparent",
                  borderRadius: "var(--radius-sm)",
                  cursor: "pointer",
                  minHeight: "44px",
                }}
              >
                {proj}
              </button>
            ))}
          </div>
          <button
            onClick={() => setStatus("idle")}
            className="mt-2 text-xs"
            style={{ color: "var(--text-muted)", cursor: "pointer", minHeight: "44px" }}
          >
            취소
          </button>
        </div>
      )}
    </div>
  );
}
