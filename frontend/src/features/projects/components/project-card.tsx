"use client";

import Link from "next/link";
import type { Project } from "../types";
import {
  VISIBILITY_COLOR_VAR,
  VISIBILITY_ICON,
  VISIBILITY_LABELS,
} from "./visibility-badge";

interface ProjectCardProps {
  project: Project;
}

const STATUS_COLORS: Record<string, string> = {
  active: "var(--status-active)",
  completed: "var(--status-completed)",
  archived: "var(--status-archived)",
};

const STATUS_LABELS: Record<string, string> = {
  active: "진행 중",
  completed: "완료",
  archived: "보관",
};

export function ProjectCard({ project }: ProjectCardProps) {
  return (
    <Link
      href={`/projects/${project.id}`}
      data-testid={`project-card-${project.id}`}
      className="block p-4 rounded border transition-colors"
      style={{
        background: "var(--surface)",
        borderColor: "var(--border-subtle)",
        borderRadius: "var(--radius-md)",
      }}
      onMouseOver={(e) => {
        e.currentTarget.style.borderColor = "var(--accent)";
        e.currentTarget.style.background = "var(--surface-hover)";
      }}
      onMouseOut={(e) => {
        e.currentTarget.style.borderColor = "var(--border-subtle)";
        e.currentTarget.style.background = "var(--surface)";
      }}
    >
      {/* 제목 + status + visibility 뱃지 (Sprint 6 FE-T3) */}
      <div className="flex items-center gap-2 mb-2">
        <h3
          className="text-sm font-semibold truncate"
          style={{ color: "var(--text-primary)", fontFamily: "var(--font-display)" }}
        >
          {project.title}
        </h3>
        <span
          className="shrink-0 px-1.5 py-0.5 rounded-full text-micro font-medium"
          style={{
            // P1 fix (2026-06-01): `var(--x)20` 은 무효 CSS(배경 투명) → color-mix 로 12% tint
            // (project-detail/dashboard 및 visibility-badge 와 동일 패턴).
            background: `color-mix(in srgb, ${STATUS_COLORS[project.status]} 12%, transparent)`,
            color: STATUS_COLORS[project.status],
          }}
        >
          {STATUS_LABELS[project.status]}
        </span>
        {(() => {
          const Icon = VISIBILITY_ICON[project.visibility];
          return (
            <span
              className="shrink-0 inline-flex items-center gap-1 text-micro"
              style={{ color: VISIBILITY_COLOR_VAR[project.visibility] }}
              title={VISIBILITY_LABELS[project.visibility]}
              aria-label={`Visibility: ${VISIBILITY_LABELS[project.visibility]}`}
            >
              <Icon size={11} />
            </span>
          );
        })()}
      </div>

      {/* 태그 */}
      {project.tags.length > 0 && (
        <div className="flex items-center gap-1 flex-wrap">
          {project.tags.map((tag) => (
            <span
              key={tag}
              className="px-1.5 py-0.5 rounded-full text-micro"
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

      {/* 설명 */}
      {project.description && (
        <p
          className="mt-1.5 text-xs truncate"
          style={{ color: "var(--text-muted)" }}
        >
          {project.description}
        </p>
      )}
    </Link>
  );
}
