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
  onClick?: () => void;
  showLabel?: boolean;
}

export function VisibilityBadge({
  visibility,
  onClick,
  showLabel = true,
}: VisibilityBadgeProps) {
  const Icon = VISIBILITY_ICON[visibility];
  const color = VISIBILITY_COLOR_VAR[visibility];
  const label = VISIBILITY_LABELS[visibility];
  const isClickable = !!onClick;

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={!isClickable}
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium transition-colors"
      style={{
        background: `${color.replace("var(", "color-mix(in srgb, ").replace(")", " 12%, transparent))")}`,
        color,
        cursor: isClickable ? "pointer" : "default",
      }}
      title={isClickable ? "클릭하여 변경" : label}
      aria-label={`Visibility: ${label}`}
    >
      <Icon size={12} />
      {showLabel && <span>{label}</span>}
    </button>
  );
}
