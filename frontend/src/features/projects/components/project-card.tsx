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

const VISIBILITY_LABELS: Record<string, string> = {
  public: "공개",
  draft: "초안",
  private: "비공개",
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
        <span
          className="shrink-0 px-1.5 py-0.5 rounded-full text-[10px]"
          style={{
            background: "var(--surface-active)",
            color: "var(--text-muted)",
          }}
        >
          {VISIBILITY_LABELS[project.visibility]}
        </span>
      </div>

      {/* 통계 */}
      <div className="flex items-center gap-4 text-xs" style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
        <span>회의 {project.meetingCount}</span>
        <span>콘텐츠 {project.contentCount}</span>
        <span>액션 {project.actionItemCount}</span>
      </div>
    </a>
  );
}
