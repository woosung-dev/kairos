"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { MoreHorizontal } from "lucide-react";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { EmptyState } from "@/components/empty-state";
import { useWorkspaceRole } from "@/features/members/hooks";
import { useWorkspaceStore } from "@/features/workspaces/store";

import {
  useArchiveProject,
  useDeleteProject,
  useProject,
  useUpdateProject,
} from "../hooks";
import type { ProjectVisibility } from "../types";
import { EditProjectDialog } from "./edit-project-dialog";
import { ProjectMembersPanel } from "./project-members-panel";
import { VisibilityBadge } from "./visibility-badge";
import { VisibilityChangeDialog } from "./visibility-change-dialog";

const TABS = ["전체", "회의", "노트", "액션", "자료"] as const;

const STATUS_LABELS: Record<string, string> = {
  active: "진행 중",
  completed: "완료",
  archived: "보관",
};

const STATUS_BG: Record<string, string> = {
  active: "var(--accent-subtle)",
  completed: "rgba(52,211,153,0.1)",
  archived: "rgba(156,163,175,0.1)",
};

const STATUS_COLOR: Record<string, string> = {
  active: "var(--accent)",
  completed: "var(--success)",
  archived: "var(--text-muted)",
};

interface ProjectDetailProps {
  projectId: string;
}

const STAT_ITEMS = [
  { label: "회의", value: 0, icon: "🎙️" },
  { label: "노트", value: 0, icon: "📝" },
  { label: "액션", value: 0, icon: "✅" },
  { label: "AI 검색", value: 0, icon: "🔍" },
];

export function ProjectDetail({ projectId }: ProjectDetailProps) {
  const [activeTab, setActiveTab] = useState<(typeof TABS)[number]>("전체");
  const [visibilityDialogOpen, setVisibilityDialogOpen] = useState(false);
  const activeWorkspaceId = useWorkspaceStore((s) => s.activeWorkspaceId);
  const { data: project, isLoading, error } = useProject(activeWorkspaceId ?? undefined, projectId);
  const updateProject = useUpdateProject(activeWorkspaceId ?? undefined);
  const router = useRouter();
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [archiveAlertOpen, setArchiveAlertOpen] = useState(false);
  const [deleteAlertOpen, setDeleteAlertOpen] = useState(false);
  const { canManage, isLoading: isRoleLoading } = useWorkspaceRole(
    activeWorkspaceId ?? undefined
  );
  const deleteMutation = useDeleteProject(activeWorkspaceId ?? undefined);
  const archiveMutation = useArchiveProject(activeWorkspaceId ?? undefined);

  const handleVisibilityChange = (next: ProjectVisibility) => {
    updateProject.mutate(
      { id: projectId, data: { visibility: next } },
      {
        onSuccess: () => setVisibilityDialogOpen(false),
        onError: (err) => {
          // BE-T15: admin 미만은 403. 사용자 토스트 안내.
          alert(err instanceof Error ? err.message : "Visibility 변경 실패");
        },
      }
    );
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16 p-6">
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          프로젝트 불러오는 중...
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-16 p-6">
        <p className="text-sm" style={{ color: "var(--error)" }}>
          프로젝트를 불러오지 못했습니다
        </p>
      </div>
    );
  }

  const status = project?.status ?? "active";

  return (
    <div className="p-6">
      {/* 헤더 */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <h1
            className="text-2xl font-bold"
            style={{ fontFamily: "var(--font-display)", color: "var(--text-primary)" }}
          >
            {project?.title ?? "프로젝트"}
          </h1>
          <span
            className="px-2 py-0.5 rounded-full text-xs font-medium"
            style={{
              background: STATUS_BG[status] ?? "var(--accent-subtle)",
              color: STATUS_COLOR[status] ?? "var(--accent)",
            }}
          >
            {STATUS_LABELS[status] ?? status}
          </span>
          {project && (
            <VisibilityBadge
              visibility={project.visibility}
              isLoading={isRoleLoading}
              interactive={canManage}
              onClick={() => {
                // closure 캐싱 회피 — 핸들러는 항상 같은 참조,
                // 호출 시점에 canManage 평가하여 race-condition 차단 (BUG-H02)
                if (canManage) setVisibilityDialogOpen(true);
              }}
            />
          )}
          {canManage && (
            <DropdownMenu>
              <DropdownMenuTrigger
                className="inline-flex h-7 w-7 items-center justify-center rounded-md hover:bg-accent hover:text-accent-foreground focus-visible:outline-none"
              >
                <MoreHorizontal className="h-4 w-4" />
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => setEditDialogOpen(true)}>
                  편집
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setArchiveAlertOpen(true)}>
                  아카이브
                </DropdownMenuItem>
                <DropdownMenuItem
                  className="text-destructive focus:text-destructive"
                  onClick={() => setDeleteAlertOpen(true)}
                >
                  삭제
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          )}
        </div>
        {project?.description && (
          <p className="text-sm mb-1" style={{ color: "var(--text-secondary)" }}>
            {project.description}
          </p>
        )}
        {project?.tags && project.tags.length > 0 && (
          <div className="flex items-center gap-1 flex-wrap mt-2">
            {project.tags.map((tag) => (
              <span
                key={tag}
                className="px-2 py-0.5 rounded-full text-[11px]"
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
        <p className="text-xs mt-2" style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
          ID: {projectId}
        </p>
      </div>

      {/* Stat 카드 */}
      <div className="grid grid-cols-4 gap-3 mb-6">
        {STAT_ITEMS.map((stat) => (
          <div
            key={stat.label}
            className="p-3 rounded border"
            style={{
              background: "var(--surface)",
              borderColor: "var(--border-subtle)",
              borderRadius: "var(--radius-md)",
            }}
          >
            <div className="flex items-center gap-2 mb-1">
              <span className="text-base">{stat.icon}</span>
              <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                {stat.label}
              </span>
            </div>
            <p
              className="text-xl font-semibold"
              style={{ color: "var(--text-primary)", fontFamily: "var(--font-mono)" }}
            >
              {stat.value}
            </p>
          </div>
        ))}
      </div>

      {/* 탭 */}
      <div className="flex items-center gap-1 mb-6 border-b" style={{ borderColor: "var(--border-subtle)" }}>
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className="px-3 py-2 text-sm font-medium transition-colors"
            style={{
              color: activeTab === tab ? "var(--accent)" : "var(--text-muted)",
              borderBottom: activeTab === tab ? "2px solid var(--accent)" : "2px solid transparent",
            }}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* 콘텐츠 리스트 (빈 상태) */}
      <EmptyState
        icon="📄"
        title="콘텐츠를 추가하세요"
        description="회의, 노트, 자료를 추가하면 여기에 표시됩니다"
        action={{ label: "콘텐츠 추가", href: "/new" }}
      />

      {/* Sprint 6 FE-T4: Project 멤버 관리 패널 (시안 2A 단순화) */}
      {project && activeWorkspaceId && (
        <ProjectMembersPanel
          workspaceId={activeWorkspaceId}
          projectId={projectId}
          visibility={project.visibility}
          canManage={canManage}
        />
      )}

      {/* Sprint 6 FE-T2b: visibility 변경 모달 (시안 1C) */}
      {project && (
        <VisibilityChangeDialog
          open={visibilityDialogOpen}
          onOpenChange={setVisibilityDialogOpen}
          currentVisibility={project.visibility}
          isPending={updateProject.isPending}
          onConfirm={handleVisibilityChange}
        />
      )}

      {/* AD-34: 프로젝트 편집 다이얼로그 */}
      {project && activeWorkspaceId && (
        <EditProjectDialog
          open={editDialogOpen}
          onOpenChange={setEditDialogOpen}
          workspaceId={activeWorkspaceId}
          project={project}
        />
      )}

      {/* AD-34: 아카이브 확인 */}
      <AlertDialog open={archiveAlertOpen} onOpenChange={setArchiveAlertOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>프로젝트를 아카이브하시겠습니까?</AlertDialogTitle>
            <AlertDialogDescription>
              아카이브된 프로젝트는 목록에서 숨겨지며 나중에 복원할 수 있습니다.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>취소</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                archiveMutation.mutate(projectId, {
                  onSuccess: () => setArchiveAlertOpen(false),
                });
              }}
              disabled={archiveMutation.isPending}
            >
              아카이브
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* AD-34: 삭제 확인 */}
      <AlertDialog open={deleteAlertOpen} onOpenChange={setDeleteAlertOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>프로젝트를 삭제하시겠습니까?</AlertDialogTitle>
            <AlertDialogDescription>
              삭제된 프로젝트는 복원할 수 없습니다. 이 작업은 되돌릴 수 없습니다.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>취소</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => {
                deleteMutation.mutate(projectId, {
                  onSuccess: () => {
                    setDeleteAlertOpen(false);
                    if (activeWorkspaceId) {
                      router.push(`/workspace/${activeWorkspaceId}/projects`);
                    }
                  },
                });
              }}
              disabled={deleteMutation.isPending}
            >
              삭제
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
