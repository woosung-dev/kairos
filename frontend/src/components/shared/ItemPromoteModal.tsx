// Sprint 23 D4 — 5 도메인 generic promote modal (memory/meeting/note/inbox/action)
// Sprint 24 BL-064 — note 분기: chunk 0 + plain_text BG re-embedding polling.
// 기존 features/memory/components/PromoteModal.tsx 의 로직을 추출 + itemType dispatch.
"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowUpRight, Users } from "lucide-react";
import { useAuth } from "@clerk/nextjs";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { useWorkspaces } from "@/features/workspaces/hooks";
import { API_BASE_URL } from "@/lib/api-client";
import { memoryKeys } from "@/features/memory/api";
import { meetingKeys } from "@/features/meetings/api";
import {
  getEmbeddingStatus,
  noteKeys,
  type EmbeddingStatus,
} from "@/features/notes/api";
import { inboxKeys } from "@/features/inbox/api";
import { actionKeys } from "@/features/actions/api";

/* ── 5 도메인 타입 정의 ── */

export type PromotableItemType =
  | "memory"
  | "meeting"
  | "note"
  | "inbox"
  | "action";

export interface ItemPromoteModalProps {
  itemType: PromotableItemType;
  itemId: string;
  sourceWorkspaceId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: (newItemId: string, auditId: string) => void;
}

/* ── itemType → endpoint path 매핑 ──
 * BE 라우터 prefix 검증 결과:
 * - memory  : /api/v1/workspaces/{wid}/memory/{id}/promote
 * - meeting : /api/v1/workspaces/{wid}/meetings/{id}/promote
 * - note    : /api/v1/workspaces/{wid}/notes/{id}/promote
 * - inbox   : /api/v1/workspaces/{wid}/inbox/{id}/promote
 * - action  : /api/v1/workspaces/{wid}/action-items/{id}/promote   ← prefix 주의
 */
const ENDPOINT_SEGMENT: Record<PromotableItemType, string> = {
  memory: "memory",
  meeting: "meetings",
  note: "notes",
  inbox: "inbox",
  action: "action-items",
};

/* ── itemType → response newItemId 키 매핑 ──
 * BE schemas.py 에서 snake_case 필드명. memory.MemoryPromoteOut 패턴 정렬.
 */
const NEW_ID_KEY: Record<PromotableItemType, string> = {
  memory: "new_memory_id",
  meeting: "new_meeting_id",
  note: "new_note_id",
  inbox: "new_inbox_id",
  action: "new_action_id",
};

/* ── itemType → 사용자 노출용 label (toast / 모달 카피) ── */
const ITEM_LABEL: Record<PromotableItemType, string> = {
  memory: "메모",
  meeting: "회의",
  note: "노트",
  inbox: "Inbox 항목",
  action: "액션",
};

/* ── itemType → invalidate 대상 query keys ── */
const INVALIDATE_KEYS = {
  memory: memoryKeys.all,
  meeting: meetingKeys.all,
  note: noteKeys.all,
  inbox: inboxKeys.all,
  action: actionKeys.all,
} as const;

interface PromoteResponse {
  audit_id: string;
  status: string;
  // Sprint 24 BL-064: note 응답에 embedding_status 추가 (snake_case 보존).
  embedding_status?: EmbeddingStatus;
  // newItemId 는 itemType 별로 키가 다르므로 dynamic 접근.
  [key: string]: string | undefined;
}

// Sprint 24 BL-064: note polling 상수 (5s × 3회).
const NOTE_POLL_INTERVAL_MS = 5000;
const NOTE_POLL_MAX_ATTEMPTS = 3;

export function ItemPromoteModal({
  itemType,
  itemId,
  sourceWorkspaceId,
  open,
  onOpenChange,
  onSuccess,
}: ItemPromoteModalProps) {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();
  const { data: workspaces } = useWorkspaces();

  // 신규 생성 워크스페이스는 type 누락될 수 있으므로 personal 명시되지 않은 것만 제외.
  // (memory/components/PromoteModal.tsx 의 기존 패턴 정렬)
  const teamOptions = (workspaces ?? []).filter(
    (w) => w.type !== "personal" && w.id !== sourceWorkspaceId
  );

  const [targetId, setTargetId] = useState<string>("");
  // Sprint 24 Codex 3차 P2 fix: note polling 중 confirm button 재클릭 → duplicate
  // promote API 호출 방지. polling 동안 isDisabled 에 합산.
  const [isPolling, setIsPolling] = useState<boolean>(false);
  // Sprint 24 Gemini P1 fix: polling interval 의 unmount cleanup (memory leak +
  // setState on unmounted component 방지). useRef 로 cancellable handle 추적.
  const pollIntervalRef = useRef<number | null>(null);
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current !== null) {
        window.clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
  }, []);
  const selectedTarget = targetId || teamOptions[0]?.id || "";

  const promote = useMutation({
    mutationFn: async (targetWorkspaceId: string): Promise<PromoteResponse> => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      const segment = ENDPOINT_SEGMENT[itemType];
      const url = `${API_BASE_URL}/api/v1/workspaces/${sourceWorkspaceId}/${segment}/${itemId}/promote`;
      const res = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        // BE schemas.py 는 populate_by_name=True 라 snake_case/camelCase 둘 다 허용.
        // 명세 (Task 4 prompt) 는 camelCase targetWorkspaceId 권장 → 그대로 사용.
        body: JSON.stringify({ targetWorkspaceId }),
      });
      if (!res.ok) {
        const errBody = await res
          .json()
          .catch(() => ({ detail: "요청 실패" }));
        throw new Error(
          (errBody as { detail?: string }).detail ?? `HTTP ${res.status}`
        );
      }
      return (await res.json()) as PromoteResponse;
    },
    onSuccess: async (response, targetWorkspaceId) => {
      // 도메인별 invalidate (5 도메인 모두 list/detail 키)
      queryClient.invalidateQueries({ queryKey: INVALIDATE_KEYS[itemType] });
      const newId = response[NEW_ID_KEY[itemType]];
      const auditId = response.audit_id;

      // Sprint 24 BL-064 — note 분기: embedding_status pending/processing 이면 polling.
      // snake_case 보존 — BE 응답 alias 없음 (Codex 2차 P2-3).
      if (
        itemType === "note" &&
        newId &&
        auditId &&
        (response.embedding_status === "pending" ||
          response.embedding_status === "processing")
      ) {
        // Sprint 24 Codex 3차 P2 fix: polling 동안 confirm button disable
        // (mutation.isPending 이 false 로 되돌아가는 시점에도 isPolling 으로 차단).
        setIsPolling(true);
        const toastId = toast.loading("노트 복사 완료 (임베딩 재생성 중)");
        let attempts = 0;
        // Sprint 24 Gemini P1 fix: ref 에 interval handle 저장 — unmount cleanup 가능.
        const intervalId = window.setInterval(async () => {
          attempts += 1;
          try {
            const token = await getToken();
            if (!token) {
              window.clearInterval(intervalId);
              setIsPolling(false);
              toast.error("상태 확인 실패", { id: toastId });
              onOpenChange(false);
              return;
            }
            const status = await getEmbeddingStatus(
              token,
              targetWorkspaceId,
              newId,
            );
            if (status.status === "completed") {
              window.clearInterval(intervalId);
              setIsPolling(false);
              toast.success("임베딩 재생성 완료", { id: toastId });
              onSuccess?.(newId, auditId);
              onOpenChange(false);
            } else if (status.status === "failed") {
              window.clearInterval(intervalId);
              setIsPolling(false);
              toast.error("임베딩 재생성 실패", { id: toastId });
              onOpenChange(false);
            } else if (attempts >= NOTE_POLL_MAX_ATTEMPTS) {
              window.clearInterval(intervalId);
              setIsPolling(false);
              toast("재생성이 계속 진행 중이에요. 잠시 후 새로고침하세요", {
                id: toastId,
              });
              onSuccess?.(newId, auditId);
              onOpenChange(false);
            }
          } catch {
            window.clearInterval(intervalId);
            setIsPolling(false);
            toast.error("상태 확인 실패", { id: toastId });
            onOpenChange(false);
          }
        }, NOTE_POLL_INTERVAL_MS);
        pollIntervalRef.current = intervalId;
        return;
      }

      // 기존 도메인 동작 — 즉시 success + close.
      toast.success(`${ITEM_LABEL[itemType]}을(를) 팀에 복사 중…`);
      if (newId && auditId) onSuccess?.(newId, auditId);
      onOpenChange(false);
    },
    onError: (err: Error) => {
      toast.error(err.message || "팀으로 올리는 데 실패했어요");
    },
  });

  const isDisabled =
    !selectedTarget ||
    promote.isPending ||
    isPolling ||
    teamOptions.length === 0;

  async function handleConfirm() {
    if (!selectedTarget) return;
    await promote.mutateAsync(selectedTarget);
  }

  // Sprint 24 Gemini P1 fix: polling 중 manual close 차단 (Escape / overlay 클릭 무시).
  // 단 polling 자체의 timeout/completed/failed 분기에서는 직접 onOpenChange(false) 호출 OK.
  const handleOpenChange = (nextOpen: boolean) => {
    if (!nextOpen && isPolling) return;
    onOpenChange(nextOpen);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="text-lg">팀으로 올리기</DialogTitle>
          <DialogDescription>
            어느 팀 워크스페이스로 보낼까요? 원본은 그대로 유지됩니다.
          </DialogDescription>
        </DialogHeader>

        <div className="mt-2">
          <label
            htmlFor="promote-target"
            className="mb-2 block text-caption font-medium uppercase tracking-wide text-muted-foreground"
          >
            대상 워크스페이스
          </label>
          <div className="relative">
            <Users className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <select
              id="promote-target"
              value={selectedTarget}
              onChange={(event) => setTargetId(event.target.value)}
              disabled={teamOptions.length === 0 || promote.isPending}
              className="h-11 w-full appearance-none rounded-md border border-input bg-background pl-9 pr-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
            >
              {teamOptions.length === 0 && (
                <option value="">팀 워크스페이스가 없어요</option>
              )}
              {teamOptions.map((workspace) => (
                <option key={workspace.id} value={workspace.id}>
                  {workspace.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="mt-6 flex justify-end gap-2">
          <Button
            type="button"
            variant="ghost"
            onClick={() => onOpenChange(false)}
            disabled={promote.isPending || isPolling}
          >
            취소
          </Button>
          <Button type="button" onClick={handleConfirm} disabled={isDisabled}>
            <ArrowUpRight className="mr-2 h-4 w-4" />
            {promote.isPending ? "복사 중…" : "팀으로 올리기"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
