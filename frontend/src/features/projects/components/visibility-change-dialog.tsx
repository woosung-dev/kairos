// Project visibility 변경 모달 (Sprint 6 FE-T2b, 시안 1C)
"use client";

import { ArrowRight } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

import type { ProjectVisibility } from "../types";
import {
  VISIBILITY_COLOR_VAR,
  VISIBILITY_DESCRIPTIONS,
  VISIBILITY_ICON,
  VISIBILITY_LABELS,
  VisibilityBadge,
} from "./visibility-badge";

interface VisibilityChangeDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  currentVisibility: ProjectVisibility;
  isPending: boolean;
  onConfirm: (next: ProjectVisibility) => void;
}

const OPTIONS: ProjectVisibility[] = ["public", "draft", "private"];

export function VisibilityChangeDialog({
  open,
  onOpenChange,
  currentVisibility,
  isPending,
  onConfirm,
}: VisibilityChangeDialogProps) {
  const [next, setNext] = useState<ProjectVisibility>(currentVisibility);

  const handleConfirm = () => {
    if (next === currentVisibility) {
      onOpenChange(false);
      return;
    }
    onConfirm(next);
  };

  const isPrivateChange = next === "private" && currentVisibility !== "private";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[480px]">
        <DialogHeader>
          <DialogTitle>Visibility 변경</DialogTitle>
          <DialogDescription>
            프로젝트 가시성을 변경합니다. admin 이상만 변경 가능.
          </DialogDescription>
        </DialogHeader>

        {/* Public → Private transition (1C 시안) */}
        <div className="flex items-center justify-center gap-3 py-4">
          <VisibilityBadge visibility={currentVisibility} showLabel />
          <ArrowRight size={16} style={{ color: "var(--text-muted)" }} />
          <VisibilityBadge visibility={next} showLabel />
        </div>

        {/* visibility 옵션 라디오 */}
        <div className="space-y-2">
          {OPTIONS.map((opt) => {
            const Icon = VISIBILITY_ICON[opt];
            const isSelected = next === opt;
            return (
              <button
                key={opt}
                type="button"
                onClick={() => setNext(opt)}
                className="w-full flex items-start gap-3 p-3 text-left rounded transition-colors"
                style={{
                  background: isSelected
                    ? "var(--accent-subtle)"
                    : "var(--surface)",
                  border: `1px solid ${isSelected ? "var(--accent)" : "var(--border-subtle)"}`,
                  borderRadius: "var(--radius-md)",
                }}
              >
                <Icon size={20} style={{ color: VISIBILITY_COLOR_VAR[opt] }} />
                <div className="flex-1 min-w-0">
                  <div
                    className="text-sm font-medium"
                    style={{ color: "var(--text-primary)" }}
                  >
                    {VISIBILITY_LABELS[opt]}
                  </div>
                  <div
                    className="text-xs mt-0.5"
                    style={{ color: "var(--text-secondary)" }}
                  >
                    {VISIBILITY_DESCRIPTIONS[opt]}
                  </div>
                </div>
              </button>
            );
          })}
        </div>

        {/* warning alert (Private 변경 시) */}
        {isPrivateChange && (
          <div
            className="mt-3 p-3 text-xs rounded"
            style={{
              background: "rgba(251,191,36,0.1)",
              borderLeft: "3px solid var(--warning)",
              color: "var(--text-secondary)",
              borderRadius: "var(--radius-sm)",
            }}
          >
            ⚠️ Private 변경 시 비멤버는 즉시 접근 차단되고 RAG 검색 결과에서도 제외됩니다.
            기존 워크스페이스 멤버를 ProjectMember로 추가하려면 변경 후 멤버 패널을 사용하세요.
          </div>
        )}

        <DialogFooter>
          <Button
            variant="ghost"
            onClick={() => onOpenChange(false)}
            disabled={isPending}
          >
            취소
          </Button>
          <Button
            onClick={handleConfirm}
            disabled={isPending || next === currentVisibility}
          >
            {isPending ? "변경 중..." : "변경"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
