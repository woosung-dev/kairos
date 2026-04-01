"use client";

import type { Project } from "../types";
import { ProjectCard } from "./project-card";
import { EmptyState } from "@/components/empty-state";

interface ProjectListProps {
  projects: Project[];
}

export function ProjectList({ projects }: ProjectListProps) {
  if (projects.length === 0) {
    return (
      <EmptyState
        icon="📁"
        title="프로젝트가 없습니다"
        description="첫 번째 프로젝트를 만들어 콘텐츠를 정리하세요"
        action={{ label: "프로젝트 만들기", href: "/new" }}
      />
    );
  }

  return (
    <div className="grid gap-3">
      {projects.map((project) => (
        <ProjectCard key={project.id} project={project} />
      ))}
    </div>
  );
}
