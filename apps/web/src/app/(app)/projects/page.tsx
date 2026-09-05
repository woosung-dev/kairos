// 프로젝트 목록 페이지 — Sprint 24 Wave 2 T-PROJ-LIST (BUG-CASUAL-001) sidebar dead-end fix
"use client";

import { useState } from "react";
import { Plus, Folder } from "lucide-react";
import { useProjects } from "@/features/projects/hooks";
import type { ProjectStatus } from "@/features/projects/types";
import { useWorkspaceStore } from "@/features/workspaces/store";
import { ProjectCard } from "@/features/projects/components/project-card";
import { CreateProjectDialog } from "@/features/projects/components/create-project-dialog";
import { EmptyState } from "@/components/empty-state";
import { OnboardingTooltip } from "@/components/onboarding/onboarding-tooltip";

// 상태 필터 — 이전엔 active 만 조회해 완료(completed) 프로젝트가 목록·사이드바 어디에도 안 보였다.
const STATUS_TABS: { value: ProjectStatus; label: string }[] = [
  { value: "active", label: "진행 중" },
  { value: "completed", label: "완료" },
  { value: "archived", label: "보관" },
];

const EMPTY_COPY: Record<ProjectStatus, { title: string; description: string }> = {
  active: {
    title: "프로젝트가 없습니다",
    description: "첫 번째 프로젝트를 만들어 콘텐츠를 정리하세요",
  },
  completed: {
    title: "완료된 프로젝트가 없습니다",
    description: "프로젝트 편집에서 상태를 완료로 바꾸면 여기에 모입니다",
  },
  archived: {
    title: "보관된 프로젝트가 없습니다",
    description: "프로젝트 관리 메뉴의 아카이브로 보관할 수 있습니다",
  },
};

export default function ProjectsPage() {
  const activeWorkspaceId = useWorkspaceStore((s) => s.activeWorkspaceId);
  const hasRole = useWorkspaceStore((s) => s.hasRole);
  const canWrite = hasRole("member");
  const [status, setStatus] = useState<ProjectStatus>("active");
  const { data, isLoading, error } = useProjects(
    activeWorkspaceId ?? undefined,
    { status },
  );
  const [isCreateOpen, setIsCreateOpen] = useState(false);

  const projects = data?.items ?? [];
  const isEmpty = !isLoading && !error && projects.length === 0;
  // 온보딩 툴팁은 "진행 중 프로젝트가 하나도 없을 때" 만 의미가 있다
  const isActiveEmpty = status === "active" && isEmpty;

  return (
    <div className="px-6 py-8 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1
          className="text-2xl font-bold"
          style={{
            fontFamily: "var(--font-display)",
            color: "var(--text-primary)",
          }}
        >
          프로젝트
        </h1>
        {canWrite && activeWorkspaceId && (
          // Sprint 24 Wave 2 T-PROJ-LIST: OnboardingTooltip step<2 + empty 시 발화 (조건부 gate)
          <OnboardingTooltip page="projects" isEmpty={isActiveEmpty}>
            <button
              type="button"
              data-testid="create-project-button"
              onClick={() => setIsCreateOpen(true)}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded text-sm font-medium transition-colors"
              style={{
                background: "var(--accent)",
                color: "var(--background)",
                borderRadius: "var(--radius-sm)",
              }}
            >
              <Plus size={14} />
              <span>새 프로젝트</span>
            </button>
          </OnboardingTooltip>
        )}
      </div>

      {/* 상태 필터 pill */}
      <div className="flex items-center gap-1 mb-5" role="tablist" aria-label="프로젝트 상태 필터">
        {STATUS_TABS.map((tab) => {
          const isActive = tab.value === status;
          return (
            <button
              key={tab.value}
              type="button"
              role="tab"
              aria-selected={isActive}
              data-testid={`projects-status-${tab.value}`}
              onClick={() => setStatus(tab.value)}
              className="px-3 py-1.5 rounded-full text-xs font-medium transition-colors cursor-pointer"
              style={{
                background: isActive ? "var(--accent-subtle)" : "transparent",
                color: isActive ? "var(--accent)" : "var(--text-muted)",
                border: isActive
                  ? "1px solid var(--accent)"
                  : "1px solid var(--border-subtle)",
              }}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            프로젝트 불러오는 중...
          </p>
        </div>
      ) : error ? (
        <div className="flex items-center justify-center py-16">
          <p className="text-sm" style={{ color: "var(--error)" }}>
            프로젝트를 불러오지 못했습니다
          </p>
        </div>
      ) : isEmpty ? (
        <div data-testid="projects-empty-state">
          <EmptyState
            icon={<Folder className="w-10 h-10" />}
            title={EMPTY_COPY[status].title}
            description={EMPTY_COPY[status].description}
            // Codex F-7 fix: /new (content add) 가 아닌 CreateProjectDialog 열기
            action={
              canWrite && status === "active"
                ? { label: "새 프로젝트", onClick: () => setIsCreateOpen(true) }
                : undefined
            }
          />
        </div>
      ) : (
        <div
          data-testid="projects-grid"
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3"
        >
          {projects.map((project) => (
            <ProjectCard key={project.id} project={project} />
          ))}
        </div>
      )}

      {activeWorkspaceId && (
        <CreateProjectDialog
          open={isCreateOpen}
          onOpenChange={setIsCreateOpen}
          workspaceId={activeWorkspaceId}
        />
      )}
    </div>
  );
}
