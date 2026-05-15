// 워크스페이스 타입 배지 (Personal=Lock / Team=Users) — DESIGN.md §Workspace Types lock-in
"use client";

import { Lock, Users } from "lucide-react";
import type { Workspace } from "../types";
import { inferWorkspaceType } from "../utils";

type Size = "sm" | "md";

interface WorkspaceTypeBadgeProps {
  workspace: Pick<Workspace, "name" | "type">;
  size?: Size;
  withLabel?: boolean;
  className?: string;
}

const ICON_PX: Record<Size, number> = { sm: 10, md: 12 };

export function WorkspaceTypeBadge({
  workspace,
  size = "sm",
  withLabel = false,
  className,
}: WorkspaceTypeBadgeProps) {
  const type = inferWorkspaceType(workspace);
  const isPersonal = type === "personal";

  const Icon = isPersonal ? Lock : Users;
  const iconSize = ICON_PX[size];
  const label = isPersonal ? "Personal" : "Team";

  return (
    <span
      className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[11px] ${className ?? ""}`}
      style={{
        fontFamily: "var(--font-mono)",
        background: isPersonal ? "var(--surface-active)" : "var(--accent-subtle)",
        color: isPersonal ? "var(--text-muted)" : "var(--accent)",
        lineHeight: 1,
      }}
      aria-label={`${label} workspace`}
      title={`${label} workspace`}
    >
      <Icon size={iconSize} aria-hidden />
      {withLabel && <span>{label}</span>}
    </span>
  );
}
