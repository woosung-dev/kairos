"use client";

import { memo, useState } from "react";
import type { LucideIcon } from "lucide-react";
import { ArrowUpRight, Mic, StickyNote, Paperclip, Pin, Check, Pencil, Trash2, Undo2 } from "lucide-react";
import { ItemPromoteModal } from "@/components/shared/ItemPromoteModal";
import { useWorkspaceStore } from "@/features/workspaces/store";
import { useProjects } from "@/features/projects/hooks";
import { useDismissInbox, useClassifyInbox } from "../hooks";
import type { InboxItem } from "../types";

/* ── 라벨/아이콘 맵 ── */

const SOURCE_LABELS: Record<string, string> = {
  meeting: "회의",
  note: "노트",
  attachment: "자료",
};

const SOURCE_ICONS: Record<string, LucideIcon> = {
  meeting: Mic,
  note: StickyNote,
  attachment: Paperclip,
};

/* ── Props ── */

interface SmartInboxItemCardProps {
  item: InboxItem;
}

/* ── 컴포넌트 ── */

// React Compiler revert(zustand hasRole 비반응형 get() 과 stale 메모이제이션 충돌) 후
// 수동 memo fallback — item 단일 prop + React Query structural sharing 으로 참조 안정,
// 리스트 내 타 카드 변경 시 재렌더 차단 (439줄 최대 리스트 아이템).
function SmartInboxItemCardImpl({ item }: SmartInboxItemCardProps) {
  const [status, setStatus] = useState<"idle" | "confirmed" | "dismissed" | "editing">("idle");
  const [isPromoteOpen, setIsPromoteOpen] = useState(false);
  const activeWorkspaceId = useWorkspaceStore((s) => s.activeWorkspaceId);
  // Sprint 25 BL-069 fix: dismiss 가 BE persist 되도록 mutation wire.
  // 기존 setStatus 만 호출 → 새로고침 시 dismissed 항목 재출현 회귀. 사용자 결정 손실.
  const dismissMutation = useDismissInbox(activeWorkspaceId ?? undefined);
  // S28b 기능추가: inbox classify persistence + "다른 프로젝트" picker.
  // 기존 handleConfirm/editing 은 local state 만 변경(미persist) → classify mutation wire.
  const classifyMutation = useClassifyInbox(activeWorkspaceId ?? undefined);
  const { data: projectsData } = useProjects(activeWorkspaceId ?? undefined, {
    status: "active",
  });
  const projects = projectsData?.items ?? [];
  const [selectedProjectId, setSelectedProjectId] = useState<string>(
    item.aiSuggestedProjectId ?? ""
  );

  /* aiConfidence가 null일 때 0으로 폴백 */
  const confidencePercent = item.aiConfidence !== null
    ? Math.round(item.aiConfidence * 100)
    : null;

  /* isProcessed === true → 자동 처리된 아이템 */
  const isAutoProcessed = item.isProcessed;

  function handleConfirm() {
    // AI 제안 프로젝트가 있으면 그곳으로 classify(persist), 없으면 picker 오픈.
    if (!item.aiSuggestedProjectId) {
      setStatus("editing");
      return;
    }
    setStatus("confirmed");
    classifyMutation.mutate(
      { id: item.id, projectIds: [item.aiSuggestedProjectId] },
      { onError: () => setStatus("idle") }
    );
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

  function handleClassifyToSelected() {
    if (!selectedProjectId) return;
    setStatus("confirmed");
    classifyMutation.mutate(
      { id: item.id, projectIds: [selectedProjectId] },
      { onError: () => setStatus("editing") }
    );
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
        <Check className="w-4 h-4 shrink-0" style={{ color: "var(--success)" }} />
        <span className="text-sm flex-1" style={{ color: "var(--text-secondary)" }}>
          {item.title} &rarr;{" "}
          <strong style={{ color: "var(--accent)" }}>
            {item.aiSuggestedProjectTitle ?? "프로젝트"}
          </strong>
        </span>
        <button
          onClick={handleRevert}
          className="inline-flex items-center gap-1.5 text-xs px-2 py-1 rounded border transition-colors"
          style={{
            borderColor: "var(--border)",
            color: "var(--text-muted)",
            borderRadius: "var(--radius-sm)",
            cursor: "pointer",
            minHeight: "44px",
          }}
        >
          <Undo2 className="w-3.5 h-3.5" />
          되돌리기
        </button>
      </div>
    );
  }

  if (status === "dismissed") {
    // F-2B v1 (codex 2차 P2): handleDismiss BE persist 후 거짓 '되돌리기'
    // affordance 제거 → 정적 "무시되었습니다" 표시.
    //
    // F-2B v3 (codex+agy 2차 A/B fix):
    // - WCAG: container opacity 제거 → 텍스트 가독성 회복 (이전 v2 0.7 이
    //   페이지 배경과 블렌딩되어 실 대비 3.32:1 / 2.91:1 → AA 4.5:1 미달).
    //   대신 Trash2 아이콘과 line-through title 에만 개별 opacity 적용으로 시각
    //   de-emphasis 유지.
    // - a11y: role="status" + aria-live 제거 — useDismissInbox onSuccess 의
    //   sonner toast 가 이미 "항목을 무시했습니다" announce → double 중복
    //   회피 + refetch unmount 시 음성 끊김 회피.
    return (
      <div
        className="px-4 py-3 rounded-lg border flex items-center gap-3"
        style={{
          background: "var(--surface)",
          borderColor: "var(--border-subtle)",
          borderRadius: "var(--radius-lg)",
        }}
      >
        <Trash2 className="w-4 h-4 shrink-0" aria-hidden="true" style={{ color: "var(--text-muted)", opacity: 0.6 }} />
        <span
          className="text-sm flex-1 line-through"
          style={{ color: "var(--text-muted)", opacity: 0.7 }}
        >
          {item.title}
        </span>
        <span
          className="text-xs px-2"
          style={{
            color: "var(--text-secondary)",
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
        {(() => {
          const SourceIcon = SOURCE_ICONS[item.sourceType] ?? Pin;
          return <SourceIcon className="w-5 h-5 shrink-0" style={{ color: "var(--text-muted)" }} />;
        })()}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-sm font-semibold truncate" style={{ color: "var(--text-primary)" }}>
              {item.title}
            </h3>
            <span
              className="shrink-0 px-1.5 py-0.5 rounded-full text-micro"
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
              className="px-1.5 py-0.5 rounded text-micro"
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
              className="text-micro ml-auto"
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
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition-colors"
            style={{
              background: "var(--accent)",
              color: "var(--background)",
              borderRadius: "var(--radius-sm)",
              cursor: "pointer",
              minHeight: "44px",
            }}
          >
            <Check className="w-4 h-4" />
            확정
          </button>
          <button
            onClick={handleEdit}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition-colors border"
            style={{
              borderColor: "var(--accent)",
              color: "var(--accent)",
              borderRadius: "var(--radius-sm)",
              cursor: "pointer",
              minHeight: "44px",
            }}
          >
            <Pencil className="w-4 h-4" />
            다른 프로젝트
          </button>
          <button
            onClick={handleDismiss}
            disabled={dismissMutation.isPending}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition-colors border disabled:opacity-50 disabled:cursor-not-allowed"
            style={{
              borderColor: "var(--border)",
              color: "var(--text-muted)",
              borderRadius: "var(--radius-sm)",
              cursor: "pointer",
              minHeight: "44px",
            }}
          >
            <Trash2 className="w-4 h-4" />
            무시
          </button>
        </div>
      ) : (
        /* 자동 처리된 아이템: 수정 / 되돌리기 */
        <div className="flex items-center gap-2">
          <button
            onClick={handleEdit}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition-colors border"
            style={{
              borderColor: "var(--accent)",
              color: "var(--accent)",
              borderRadius: "var(--radius-sm)",
              cursor: "pointer",
              minHeight: "44px",
            }}
          >
            <Pencil className="w-4 h-4" />
            수정
          </button>
          <button
            onClick={handleDismiss}
            disabled={dismissMutation.isPending}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition-colors border disabled:opacity-50 disabled:cursor-not-allowed"
            style={{
              borderColor: "var(--border)",
              color: "var(--text-muted)",
              borderRadius: "var(--radius-sm)",
              cursor: "pointer",
              minHeight: "44px",
            }}
          >
            <Undo2 className="w-4 h-4" />
            되돌리기
          </button>
        </div>
      )}

      {/* "다른 프로젝트" 편집 모드 — 프로젝트 선택 picker (S28b 기능추가) */}
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
          {projects.length === 0 ? (
            <p className="text-xs mb-2" style={{ color: "var(--text-muted)" }}>
              연결할 프로젝트가 없습니다. 먼저 프로젝트를 만들어주세요.
            </p>
          ) : (
            <select
              value={selectedProjectId}
              onChange={(e) => setSelectedProjectId(e.target.value)}
              className="w-full px-2 py-1.5 mb-2 rounded border text-sm bg-transparent outline-none"
              style={{
                borderColor: "var(--border)",
                color: "var(--text-primary)",
                borderRadius: "var(--radius-sm)",
              }}
              aria-label="프로젝트 선택"
            >
              <option value="">프로젝트 선택...</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.title}
                </option>
              ))}
            </select>
          )}
          <div className="flex items-center gap-2">
            <button
              onClick={handleClassifyToSelected}
              disabled={!selectedProjectId || classifyMutation.isPending}
              className="px-3 py-1.5 rounded text-xs font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              style={{
                background: "var(--accent)",
                color: "var(--background)",
                borderRadius: "var(--radius-sm)",
                cursor: "pointer",
                minHeight: "44px",
              }}
            >
              이 프로젝트로 이동
            </button>
            <button
              onClick={() => setStatus("idle")}
              className="text-xs"
              style={{ color: "var(--text-muted)", cursor: "pointer", minHeight: "44px" }}
            >
              취소
            </button>
          </div>
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

export const SmartInboxItemCard = memo(SmartInboxItemCardImpl);
