"use client";

import { Folder } from "lucide-react";
import { useProjects } from "../hooks";
import { useWorkspaceStore } from "@/features/workspaces/store";
import { ProjectCard } from "./project-card";
import { EmptyState } from "@/components/empty-state";

export function ProjectList() {
  const activeWorkspaceId = useWorkspaceStore((s) => s.activeWorkspaceId);
  const { data, isLoading, error } = useProjects(activeWorkspaceId ?? undefined);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          프로젝트 불러오는 중...
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-16">
        <p className="text-sm" style={{ color: "var(--error)" }}>
          프로젝트를 불러오지 못했습니다
        </p>
      </div>
    );
  }

  const projects = data?.items ?? [];

  if (projects.length === 0) {
    return (
      <EmptyState
        icon={<Folder className="w-10 h-10" />}
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
