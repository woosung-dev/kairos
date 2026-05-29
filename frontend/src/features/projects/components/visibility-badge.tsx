// Project visibility 배지 (Sprint 6 FE-T2a, 시안 1A)
"use client";

import { FileEdit, Globe, Lock, type LucideIcon } from "lucide-react";

import type { ProjectVisibility } from "../types";

export const VISIBILITY_ICON: Record<ProjectVisibility, LucideIcon> = {
  public: Globe,
  draft: FileEdit,
  private: Lock,
};

export const VISIBILITY_COLOR_VAR: Record<ProjectVisibility, string> = {
  public: "var(--visibility-public)",
  draft: "var(--visibility-draft)",
  private: "var(--visibility-private)",
};

export const VISIBILITY_LABELS: Record<ProjectVisibility, string> = {
  public: "공개",
  draft: "작업 중",
  private: "비공개",
};

export const VISIBILITY_DESCRIPTIONS: Record<ProjectVisibility, string> = {
  public: "워크스페이스 모든 멤버 접근",
  draft: "작성자 + admin/owner만 접근",
  private: "명시적 멤버 + admin/owner만 접근",
};

interface VisibilityBadgeProps {
  visibility: ProjectVisibility;
  /** 클릭 핸들러. 항상 같은 참조로 전달하고 내부에서 권한 분기를 처리하면 race-condition 회피. */
  onClick?: () => void;
  showLabel?: boolean;
  /** 권한 fetch 중 — 버튼은 활성이지만 클릭 시 onClick 가 무동작이도록 처리하고 시각적으로 흐림. */
  isLoading?: boolean;
  /**
   * 시각상 대화형 여부. 미지정 시 onClick 유무로 추론(기존 동작).
   * onClick 은 BUG-H02 race 가드 때문에 항상 같은 참조로 전달하므로, viewer 등 비권한 사용자에게
   * "비대화형 배지"로 보이게 하려면 interactive={canManage} 로 시각상태만 분리한다 (OBS-VIEWER-VISIBILITY-BTN).
   */
  interactive?: boolean;
}

export function VisibilityBadge({
  visibility,
  onClick,
  showLabel = true,
  isLoading = false,
  interactive,
}: VisibilityBadgeProps) {
  const Icon = VISIBILITY_ICON[visibility];
  const color = VISIBILITY_COLOR_VAR[visibility];
  const label = VISIBILITY_LABELS[visibility];
  const canInteract = (interactive ?? !!onClick) && !isLoading;

  return (
    <button
      type="button"
      onClick={isLoading ? undefined : onClick}
      disabled={!canInteract}
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium transition-colors"
      style={{
        background: `${color.replace("var(", "color-mix(in srgb, ").replace(")", " 12%, transparent))")}`,
        color,
        cursor: canInteract ? "pointer" : "default",
        opacity: isLoading ? 0.6 : 1,
      }}
      title={
        isLoading
          ? "권한 확인 중..."
          : canInteract
            ? "클릭하여 변경"
            : label
      }
      aria-label={`Visibility: ${label}${isLoading ? " (로딩 중)" : ""}`}
      aria-busy={isLoading}
    >
      <Icon size={12} />
      {showLabel && <span>{label}</span>}
    </button>
  );
}
