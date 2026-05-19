// Sprint 15 R6 Memory promote modal — Sprint 23 D4 부터 generic ItemPromoteModal 의 thin wrapper.
// 사용처 (예: RecallResultCard) 호환 유지용 — 추후 cleanup 시 ItemPromoteModal 직접 호출로 전환.
"use client";

import {
  ItemPromoteModal,
  type ItemPromoteModalProps,
} from "@/components/shared/ItemPromoteModal";

interface PromoteModalProps {
  memoryId: string;
  sourceWorkspaceId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: ItemPromoteModalProps["onSuccess"];
}

/**
 * @deprecated Sprint 23 D4 — `<ItemPromoteModal itemType="memory" itemId={memoryId} ... />` 직접 사용 권장.
 */
export function PromoteModal({
  memoryId,
  sourceWorkspaceId,
  open,
  onOpenChange,
  onSuccess,
}: PromoteModalProps) {
  return (
    <ItemPromoteModal
      itemType="memory"
      itemId={memoryId}
      sourceWorkspaceId={sourceWorkspaceId}
      open={open}
      onOpenChange={onOpenChange}
      onSuccess={onSuccess}
    />
  );
}
