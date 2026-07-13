// 프로젝트 대시보드 헤더 — 제목/상태/visibility 뱃지 + canManage 관리 드롭다운 (BL-AV-1 분해)
"use client";

import { MoreHorizontal } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { Project, ProjectStatus } from "../../types";
import { VisibilityBadge } from "../visibility-badge";

/* ── 상태 라벨 ── */

const STATUS_LABELS: Record<ProjectStatus, string> = {
  active: "진행 중",
  completed: "완료",
  archived: "보관",
};

const STATUS_BG: Record<ProjectStatus, string> = {
  active: "var(--accent-subtle)",
  completed: "rgba(52,211,153,0.1)",
  archived: "rgba(156,163,175,0.1)",
};

const STATUS_COLOR: Record<ProjectStatus, string> = {
  active: "var(--accent)",
  completed: "var(--success)",
  archived: "var(--text-muted)",
};

export function DashboardHeader({
  project,
  canManage,
  isRoleLoading,
  onVisibilityClick,
  onEditClick,
  onArchiveClick,
  onDeleteClick,
}: {
  project: Project;
  canManage: boolean;
  isRoleLoading: boolean;
  onVisibilityClick: () => void;
  onEditClick: () => void;
  onArchiveClick: () => void;
  onDeleteClick: () => void;
}) {
  return (
    <div className="mb-6">
      <div className="flex items-center gap-3 mb-2">
        <h1
          className="text-2xl font-bold"
          style={{ fontFamily: "var(--font-display)", color: "var(--text-primary)" }}
        >
          {project.title}
        </h1>
        <span
          className="px-2 py-0.5 rounded-full text-xs font-medium"
          style={{
            background: STATUS_BG[project.status],
            color: STATUS_COLOR[project.status],
          }}
        >
          {STATUS_LABELS[project.status]}
        </span>
        <VisibilityBadge
          visibility={project.visibility}
          isLoading={isRoleLoading}
          interactive={canManage}
          onClick={() => {
            // closure 캐싱 회피 (BUG-H02) — 호출 시점 canManage 평가
            if (canManage) onVisibilityClick();
          }}
        />
        {canManage && (
          <DropdownMenu>
            <DropdownMenuTrigger
              className="inline-flex items-center justify-center h-7 w-7 rounded-md hover:bg-[var(--surface-hover)] transition-colors"
            >
              <MoreHorizontal className="h-4 w-4" style={{ color: "var(--text-muted)" }} />
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={onEditClick}>편집</DropdownMenuItem>
              <DropdownMenuItem onClick={onArchiveClick}>아카이브</DropdownMenuItem>
              <DropdownMenuItem
                className="text-destructive focus:text-destructive"
                onClick={onDeleteClick}
              >
                삭제
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>
      {project.description && (
        <p className="text-sm mb-3" style={{ color: "var(--text-secondary)" }}>
          {project.description}
        </p>
      )}
      {project.tags.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {project.tags.map((tag) => (
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
    </div>
  );
}
