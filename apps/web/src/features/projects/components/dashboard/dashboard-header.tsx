// 프로젝트 대시보드 헤더 — 제목/상태/visibility 뱃지 + 관리 드롭다운 (BL-AV-1 분해)
// 권한: 편집·visibility = admin 이상 또는 프로젝트 작성자(canEdit) / 아카이브·삭제 = admin 이상(canManage)
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
  canEdit,
  isRoleLoading,
  onVisibilityClick,
  onEditClick,
  onArchiveClick,
  onDeleteClick,
}: {
  project: Project;
  /** admin/owner — 아카이브·삭제 */
  canManage: boolean;
  /** admin/owner 또는 작성자 — 편집·visibility 변경 (2026-09-27 결정: 작성자는 member 여도 visibility 변경 가능) */
  canEdit: boolean;
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
          interactive={canEdit}
          onClick={() => {
            // closure 캐싱 회피 (BUG-H02) — 호출 시점 canEdit 평가
            if (canEdit) onVisibilityClick();
          }}
        />
        {canEdit && (
          <DropdownMenu>
            <DropdownMenuTrigger
              aria-label="프로젝트 관리 메뉴"
              className="inline-flex items-center justify-center h-7 w-7 rounded-md hover:bg-[var(--surface-hover)] transition-colors"
            >
              <MoreHorizontal className="h-4 w-4" style={{ color: "var(--text-muted)" }} />
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={onEditClick}>편집</DropdownMenuItem>
              {canManage && (
                <>
                  <DropdownMenuItem onClick={onArchiveClick}>아카이브</DropdownMenuItem>
                  <DropdownMenuItem
                    className="text-destructive focus:text-destructive"
                    onClick={onDeleteClick}
                  >
                    삭제
                  </DropdownMenuItem>
                </>
              )}
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
