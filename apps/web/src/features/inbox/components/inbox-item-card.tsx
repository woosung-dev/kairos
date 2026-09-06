"use client";

import { memo, useState } from "react";
import type { LucideIcon } from "lucide-react";
import { ArrowUpRight, Mic, StickyNote, Paperclip, Pin, Check, Pencil, Trash2, Undo2 } from "lucide-react";
import { ItemPromoteModal } from "@/components/shared/ItemPromoteModal";
import { useWorkspaceStore } from "@/features/workspaces/store";
import { useProjectTitleMap } from "@/features/projects/hooks";
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
  // 제목 해석은 전 상태 프로젝트 맵을 쓴다 — active 20건만 보면 완료·보관 프로젝트를 가리키는 추천이
  // "목록에 없음" 으로 떨어져 AI 가 지어낸 제목이 다시 노출됐다 (PR #189 P1 의 잔여 분기).
  const {
    byStatus,
    titleMap,
    isReady: isProjectMapReady,
    isError: isProjectMapError,
    isSettled: isProjectMapSettled,
    isTruncated: isProjectMapTruncated,
  } = useProjectTitleMap(activeWorkspaceId ?? undefined);
  // classify 대상 picker 는 진행 중 프로젝트만 — 완료·보관 프로젝트에 새 항목을 넣지 않는다 (기존 동작 유지).
  const projects = byStatus.active;
  const [selectedProjectId, setSelectedProjectId] = useState<string>(
    item.aiSuggestedProjectId ?? ""
  );
  // picker 에 실제로 있는 옵션만 제출 가능 — 완료·보관·권한 밖 추천 id 가 select 에 매칭 옵션 없이 숨은 채
  // "이 프로젝트로 이동" 으로 전송되던 구멍을 막는다 (2026-09-06 review, codex P1).
  const pickerProjectId = projects.some((p) => p.id === selectedProjectId) ? selectedProjectId : "";
  // 추천 id 가 있는데 프로젝트 맵이 없으면(로딩 중·조회 실패) 확정을 막는다 — 검증 전 id 로 classify 하지 않는다.
  // 실패는 "불러올 수 없음" 으로 말하고 '다른 프로젝트' 경로는 남겨 둔다.
  const isConfirmBlocked = !!item.aiSuggestedProjectId && !isProjectMapReady;
  const confirmBlockedTitle = isProjectMapError
    ? "프로젝트 목록을 불러올 수 없습니다 — '다른 프로젝트' 로 지정하세요"
    : "프로젝트 목록을 불러오는 중입니다";
  // 확정된(classify 요청을 보낸) 프로젝트 id — 확정 카드에 실제 대상 제목을 보여주기 위해 추적.
  const [confirmedProjectId, setConfirmedProjectId] = useState<string | null>(null);

  // AI 추천 라벨 — 세 갈래.
  // (a) id 가 있고 맵에 있음 → 실제 제목. 파이프라인은 AI 가 지어낸 `newProjectTitle` 을 id 와 함께 저장하므로
  //     (실측: 라벨 "IR 투자 유치 전략", 실제 classify 대상은 "💡 아이디어") AI 제목을 쓰면 사용자가 다른 프로젝트로 확정한다.
  // (b) id 없음 + title 있음 → "새 프로젝트 제안". AI 제목 폴백은 여기서만.
  // (c) id 가 있는데 맵(전 상태·100건)에 없음 → "(프로젝트 없음)" (2026-09-06 design-shotgun D2-A).
  //     실제 원인은 요청자에게 보이지 않는 private/draft 프로젝트(visibility) 또는 101번째 이후 — 삭제는
  //     FK(NO ACTION) 때문에 앱이 id 를 먼저 null 로 만들어 (b) 로 간다. 그래서 "삭제됨" 이라 쓰지 않는다.
  //     맵 로딩 전에는 블록을 그리지 않아 (c) 로 잠깐 오판하지 않는다.
  const suggestedTitle = item.aiSuggestedProjectId
    ? titleMap.get(item.aiSuggestedProjectId)
    : undefined;
  const isNewProjectSuggestion = !item.aiSuggestedProjectId && !!item.aiSuggestedProjectTitle;
  // "없음" 은 맵이 완성·정착됐고 잘리지 않았을 때만 확정한다 — refetch 엇갈림·100건 초과에서는 미표시가 안전하다.
  const isSuggestedProjectMissing =
    !!item.aiSuggestedProjectId &&
    isProjectMapReady &&
    isProjectMapSettled &&
    !isProjectMapTruncated &&
    suggestedTitle === undefined;
  const suggestedLabel = isNewProjectSuggestion
    ? item.aiSuggestedProjectTitle
    : isSuggestedProjectMissing
      ? "(프로젝트 없음)"
      : suggestedTitle;
  const confirmedLabel =
    (confirmedProjectId ? titleMap.get(confirmedProjectId) : undefined) ?? "프로젝트";

  /* aiConfidence가 null일 때 0으로 폴백 */
  const confidencePercent = item.aiConfidence !== null
    ? Math.round(item.aiConfidence * 100)
    : null;

  /* isProcessed === true → 자동 처리된 아이템 */
  const isAutoProcessed = item.isProcessed;

  function handleConfirm() {
    // AI 제안 프로젝트가 있으면 그곳으로 classify(persist). 없거나(새 프로젝트 제안) 목록에 없는 id(권한 밖·미노출)면
    // 보이지 않는 프로젝트로 보내지 않고 picker 를 연다.
    if (!item.aiSuggestedProjectId || isSuggestedProjectMissing) {
      setStatus("editing");
      return;
    }
    setStatus("confirmed");
    setConfirmedProjectId(item.aiSuggestedProjectId);
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
    if (!pickerProjectId) return;
    setStatus("confirmed");
    setConfirmedProjectId(pickerProjectId);
    classifyMutation.mutate(
      { id: item.id, projectIds: [pickerProjectId] },
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
            {confirmedLabel}
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

      {/* AI 추천 프로젝트 — (a) 실제 제목 / (b) 새 프로젝트 제안 / (c) (프로젝트 없음). 규칙은 위 suggestedLabel 정의 참고 */}
      {suggestedLabel && (
        <div
          className="flex items-center gap-2 px-3 py-2 rounded mb-3"
          style={{
            background: "var(--accent-subtle)",
            borderRadius: "var(--radius-sm)",
          }}
        >
          <span className="text-xs" style={{ color: "var(--accent)" }}>
            {isNewProjectSuggestion ? "새 프로젝트 제안:" : "AI 추천:"}
          </span>
          <span
            className="text-xs font-medium"
            style={{ color: isSuggestedProjectMissing ? "var(--text-muted)" : "var(--accent)" }}
          >
            {suggestedLabel}
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
            disabled={isConfirmBlocked}
            title={isConfirmBlocked ? confirmBlockedTitle : undefined}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
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
          {!isProjectMapReady ? (
            <p className="text-xs mb-2" style={{ color: "var(--text-muted)" }}>
              {isProjectMapError
                ? "프로젝트 목록을 불러올 수 없습니다."
                : "프로젝트 목록을 불러오는 중…"}
            </p>
          ) : projects.length === 0 ? (
            <p className="text-xs mb-2" style={{ color: "var(--text-muted)" }}>
              연결할 프로젝트가 없습니다. 먼저 프로젝트를 만들어주세요.
            </p>
          ) : (
            <select
              value={pickerProjectId}
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
              disabled={!pickerProjectId || classifyMutation.isPending}
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
