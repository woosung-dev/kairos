"use client";

import { useState } from "react";
import { ArrowUpRight } from "lucide-react";
import { ItemPromoteModal } from "@/components/shared/ItemPromoteModal";
import { useWorkspaceStore } from "@/features/workspaces/store";
import { useDismissInbox } from "../hooks";
import type { InboxItem } from "../types";

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

/* ── Props ── */

interface SmartInboxItemCardProps {
  item: InboxItem;
}

/* ── 컴포넌트 ── */

export function SmartInboxItemCard({ item }: SmartInboxItemCardProps) {
  const [status, setStatus] = useState<"idle" | "confirmed" | "dismissed" | "editing">("idle");
  const [isPromoteOpen, setIsPromoteOpen] = useState(false);
  const activeWorkspaceId = useWorkspaceStore((s) => s.activeWorkspaceId);
  // Sprint 25 BL-069 fix: dismiss 가 BE persist 되도록 mutation wire.
  // 기존 setStatus 만 호출 → 새로고침 시 dismissed 항목 재출현 회귀. 사용자 결정 손실.
  const dismissMutation = useDismissInbox(activeWorkspaceId ?? undefined);

  /* aiConfidence가 null일 때 0으로 폴백 */
  const confidencePercent = item.aiConfidence !== null
    ? Math.round(item.aiConfidence * 100)
    : null;

  /* isProcessed === true → 자동 처리된 아이템 */
  const isAutoProcessed = item.isProcessed;

  function handleConfirm() {
    setStatus("confirmed");
  }

  function handleDismiss() {
    setStatus("dismissed");
    // BL-069: BE 호출. onSuccess 에서 useInbox cache 무효화 → reload 후에도 보존.
    // F5 (Sprint 25 polish, agy review): mutation 실패 시 optimistic 'dismissed' UI 롤백
    // → 사용자에게 거짓 상태 노출 차단. 토스트는 useDismissInbox onError 가 이미 처리.
    dismissMutation.mutate(item.id, {
      onError: () => setStatus("idle"),
    });
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
          {item.title} &rarr;{" "}
          <strong style={{ color: "var(--accent)" }}>
            {item.aiSuggestedProjectTitle ?? "프로젝트"}
          </strong>
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
    // F-2B fix (codex 2차 P2): handleDismiss 가 BE persist 후 cache invalidate →
    // 되돌리기 버튼은 local setState 만 → 사용자에게 거짓 UX (BE 복원 API 부재).
    // 정적 "무시되었습니다" 표시로 변경 — 되돌리기 affordance 제거 (다음 fetch 시
    // 어차피 list 에서 사라짐).
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
        <span
          className="text-xs px-2"
          style={{
            color: "var(--text-muted)",
            fontFamily: "var(--font-mono)",
          }}
        >
          무시되었습니다
        </span>
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
        <span className="text-lg shrink-0">{SOURCE_ICONS[item.sourceType] ?? "📌"}</span>
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
              {SOURCE_LABELS[item.sourceType] ?? item.sourceType}
            </span>
            {/* Sprint 23 D4: 워크스페이스 이동 — 우상단 ghost icon button */}
            {activeWorkspaceId && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setIsPromoteOpen(true);
                }}
                className="ml-auto shrink-0 px-1.5 py-1 rounded transition-colors"
                style={{
                  color: "var(--text-muted)",
                  borderRadius: "var(--radius-sm)",
                  cursor: "pointer",
                  minHeight: "32px",
                }}
                aria-label="워크스페이스 이동"
                title="워크스페이스 이동"
              >
                <ArrowUpRight className="h-3.5 w-3.5" />
              </button>
            )}
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
          {confidencePercent !== null && (
            <span
              className="text-[10px] ml-auto"
              style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}
            >
              {confidencePercent}%
            </span>
          )}
        </div>
      )}

      {/* 액션 버튼 */}
      {!isAutoProcessed ? (
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
            disabled={dismissMutation.isPending}
            className="px-3 py-1.5 rounded text-xs font-medium transition-colors border disabled:opacity-50 disabled:cursor-not-allowed"
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
            disabled={dismissMutation.isPending}
            className="px-3 py-1.5 rounded text-xs font-medium transition-colors border disabled:opacity-50 disabled:cursor-not-allowed"
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

      {/* "다른 프로젝트" 편집 모드 (P2: 실제 프로젝트 콤보박스 연동 예정) */}
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
            프로젝트를 선택하세요
          </p>
          <p className="text-xs" style={{ color: "var(--text-muted)" }}>
            프로젝트 선택 기능은 준비 중입니다.
          </p>
          <button
            onClick={() => setStatus("idle")}
            className="mt-2 text-xs"
            style={{ color: "var(--text-muted)", cursor: "pointer", minHeight: "44px" }}
          >
            취소
          </button>
        </div>
      )}

      {/* Sprint 23 D4: 워크스페이스 이동 modal */}
      {activeWorkspaceId && (
        <ItemPromoteModal
          itemType="inbox"
          itemId={item.id}
          sourceWorkspaceId={activeWorkspaceId}
          open={isPromoteOpen}
          onOpenChange={setIsPromoteOpen}
        />
      )}
    </div>
  );
}
