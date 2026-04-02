"use client";

import type { Project } from "../types";

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
    <a
      href={`/projects/${project.id}`}
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
      {/* 제목 + 뱃지 */}
      <div className="flex items-center gap-2 mb-2">
        <h3
          className="text-sm font-semibold truncate"
          style={{ color: "var(--text-primary)", fontFamily: "var(--font-display)" }}
        >
          {project.title}
        </h3>
        <span
          className="shrink-0 px-1.5 py-0.5 rounded-full text-[10px] font-medium"
          style={{
            background: `${STATUS_COLORS[project.status]}20`,
            color: STATUS_COLORS[project.status],
          }}
        >
          {STATUS_LABELS[project.status]}
        </span>
      </div>

      {/* 태그 */}
      {project.tags.length > 0 && (
        <div className="flex items-center gap-1 flex-wrap">
          {project.tags.map((tag) => (
            <span
              key={tag}
              className="px-1.5 py-0.5 rounded-full text-[10px]"
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
    </a>
  );
}
