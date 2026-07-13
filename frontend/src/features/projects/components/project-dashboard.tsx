"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle } from "lucide-react";
import { toast } from "sonner";
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
import { useWorkspaceRole } from "@/features/members/hooks";
import {
  useProject,
  useArchiveProject,
  useDeleteProject,
  useUpdateProject,
  useRecentItems,
} from "../hooks";
import { useActionItems, useUpdateActionItem } from "@/features/actions/hooks";
import { useMeetings } from "@/features/meetings/hooks";
import { useNotes } from "@/features/notes/hooks";
import { useWorkspaceStore } from "@/features/workspaces/store";
import type { ActionItem, ActionStatus } from "@/features/actions/types";
import { EditProjectDialog } from "./edit-project-dialog";
import { ProjectMembersPanel } from "./project-members-panel";
import { Skeleton } from "@/components/ui/skeleton";
import { VisibilityChangeDialog } from "./visibility-change-dialog";
import { DashboardHeader } from "./dashboard/dashboard-header";
import { MeetingCard } from "./dashboard/meeting-card";
import { NoteCard } from "./dashboard/note-card";
import { OnboardingView } from "./dashboard/onboarding-view";

/* ── 날짜 오버듀 확인 ── */

function isOverdue(dateStr: string | null): boolean {
  if (!dateStr) return false;
  const d = new Date(dateStr);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return d < today;
}

/* ── 로딩 스켈레톤 ── */

function DashboardSkeleton() {
  return (
    <div className="p-6 space-y-6">
      <Skeleton className="h-8 rounded w-1/3" />
      <Skeleton className="h-4 rounded w-2/3" />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-20 rounded-lg" />
          ))}
        </div>
        <div className="space-y-2">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-12 rounded-lg" />
          ))}
        </div>
      </div>
    </div>
  );
}

/* ── 컴포넌트 ── */

interface ProjectDashboardProps {
  projectId: string;
}

export function ProjectDashboard({ projectId }: ProjectDashboardProps) {
  const activeWorkspaceId = useWorkspaceStore((s) => s.activeWorkspaceId);
  const wid = activeWorkspaceId ?? undefined;

  const router = useRouter();
  const [visibilityDialogOpen, setVisibilityDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [archiveAlertOpen, setArchiveAlertOpen] = useState(false);
  const [deleteAlertOpen, setDeleteAlertOpen] = useState(false);
  const { canManage, isLoading: isRoleLoading } = useWorkspaceRole(wid);
  const updateProject = useUpdateProject(wid);
  const deleteMutation = useDeleteProject(wid);
  const archiveMutation = useArchiveProject(wid);

  const { data: project, isLoading: projectLoading, error: projectError } = useProject(wid, projectId);

  /* 액션 아이템: projectId 필터 지원 */
  const { data: actionsData, isLoading: actionsLoading } = useActionItems(wid, {
    projectId,
    page: 1,
    pageSize: 20,
  });

  /* 회의: projectId 필터 지원 */
  const { data: meetingsData, isLoading: meetingsLoading } = useMeetings(wid, 1, projectId);

  /* 노트 목록: projectId 필터 지원 */
  const { data: notesData, isLoading: notesLoading } = useNotes(wid, projectId);

  const updateAction = useUpdateActionItem(wid);

  /* React Hooks 규칙: 모든 훅은 early return 이전에 호출되어야 함 (ISSUE-009 fix) */
  const actions = actionsData?.items ?? [];
  const projectMeetings = meetingsData?.items ?? [];
  const notes = notesData?.items ?? [];

  /* 최근 아이템: 회의 + 노트 합쳐 날짜순 정렬, 5개 — hooks.ts:useRecentItems */
  const recentItems = useRecentItems(projectMeetings, notes);

  /* 로딩 */
  if (projectLoading) return <DashboardSkeleton />;

  /* 에러 */
  if (projectError || !project) {
    return (
      <div className="p-6 flex flex-col items-center justify-center py-20 text-center">
        <AlertTriangle className="w-10 h-10 mb-4" style={{ color: "var(--error)" }} />
        <p className="text-sm" style={{ color: "var(--error)" }}>
          프로젝트 데이터를 불러올 수 없습니다.
        </p>
      </div>
    );
  }

  const isContentLoading = actionsLoading || meetingsLoading || notesLoading;

  /* 콘텐츠 3개 미만이면 온보딩 뷰 */
  const hasContent = !isContentLoading && recentItems.length >= 3;

  function handleToggleAction(action: ActionItem) {
    const nextStatus: ActionStatus =
      action.status === "done" ? "todo" : "done";
    updateAction.mutate({ id: action.id, data: { status: nextStatus } });
  }

  if (!isContentLoading && !hasContent && recentItems.length < 3) {
    return (
      <div className="p-6">
        <DashboardHeader
          project={project}
          canManage={canManage}
          isRoleLoading={isRoleLoading}
          onVisibilityClick={() => setVisibilityDialogOpen(true)}
          onEditClick={() => setEditDialogOpen(true)}
          onArchiveClick={() => setArchiveAlertOpen(true)}
          onDeleteClick={() => setDeleteAlertOpen(true)}
        />
        <OnboardingView />
      </div>
    );
  }

  return (
    <div className="p-6">
      <DashboardHeader
        project={project}
        canManage={canManage}
        isRoleLoading={isRoleLoading}
        onVisibilityClick={() => setVisibilityDialogOpen(true)}
        onEditClick={() => setEditDialogOpen(true)}
        onArchiveClick={() => setArchiveAlertOpen(true)}
        onDeleteClick={() => setDeleteAlertOpen(true)}
      />

      {/* 프로액티브 인사이트 — BE 미지원, 섹션 숨김 */}
      {/* project 응답에 insight 필드가 추가되면 여기서 렌더링 */}

      {/* 로딩 중이면 스켈레톤 */}
      {isContentLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-20 rounded-lg" />
            ))}
          </div>
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-12 rounded-lg" />
            ))}
          </div>
        </div>
      ) : (
        /* 2컬럼 그리드 */
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* 좌: 최근 회의/노트 */}
          <div className="space-y-3">
            <h2
              className="text-sm font-semibold mb-1"
              style={{ color: "var(--text-secondary)", fontFamily: "var(--font-display)" }}
            >
              최근 회의 &middot; 노트
            </h2>
            {recentItems.length === 0 ? (
              <p className="text-xs py-4" style={{ color: "var(--text-muted)" }}>
                최근 항목이 없습니다
              </p>
            ) : (
              recentItems.map((item) =>
                item.kind === "meeting" ? (
                  <MeetingCard key={`m-${item.data.id}`} meeting={item.data} />
                ) : (
                  <NoteCard key={`n-${item.data.id}`} note={item.data} />
                )
              )
            )}
          </div>

          {/* 우: 이번 주 액션 */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <h2
                className="text-sm font-semibold"
                style={{ color: "var(--text-secondary)", fontFamily: "var(--font-display)" }}
              >
                이번 주 액션
              </h2>
            </div>
            {actions.length === 0 ? (
              <p className="text-xs py-4" style={{ color: "var(--text-muted)" }}>
                액션 아이템이 없습니다
              </p>
            ) : (
              <div className="space-y-2">
                {actions.map((action) => (
                  <ActionRow
                    key={action.id}
                    action={action}
                    onToggle={() => handleToggleAction(action)}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {wid && (
        <ProjectMembersPanel
          workspaceId={wid}
          projectId={projectId}
          visibility={project.visibility}
          canManage={canManage}
        />
      )}

      {/* 관리 컨트롤 다이얼로그 */}
      <VisibilityChangeDialog
        open={visibilityDialogOpen}
        onOpenChange={setVisibilityDialogOpen}
        currentVisibility={project.visibility}
        isPending={updateProject.isPending}
        onConfirm={(next) => {
          updateProject.mutate(
            { id: projectId, data: { visibility: next } },
            { onSuccess: () => setVisibilityDialogOpen(false) }
          );
        }}
      />

      {wid && (
        <EditProjectDialog
          open={editDialogOpen}
          onOpenChange={setEditDialogOpen}
          workspaceId={wid}
          project={project}
        />
      )}

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

      <AlertDialog open={deleteAlertOpen} onOpenChange={setDeleteAlertOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>프로젝트를 삭제하시겠습니까?</AlertDialogTitle>
            <AlertDialogDescription>
              삭제된 프로젝트는 복원할 수 없습니다.
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
                    router.push("/dashboard");
                  },
                  onError: (err) => {
                    // BL-S27e-5: 콘텐츠 연결 프로젝트는 409 → 사유 토스트, 다이얼로그 유지.
                    toast.error(err instanceof Error ? err.message : "삭제 실패");
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

/* ── 서브 컴포넌트 ── */

function ActionRow({ action, onToggle }: { action: ActionItem; onToggle: () => void }) {
  const isDone = action.status === "done";

  return (
    <div
      className="flex items-center gap-3 px-3 py-2 rounded-lg border transition-colors"
      style={{
        background: "var(--surface)",
        borderColor: "var(--border-subtle)",
        borderRadius: "var(--radius-lg)",
      }}
    >
      <input
        type="checkbox"
        checked={isDone}
        onChange={onToggle}
        className="shrink-0 w-4 h-4 rounded accent-current"
        style={{ accentColor: "var(--accent)", cursor: "pointer", minHeight: "44px", minWidth: "16px" }}
      />
      <div className="flex-1 min-w-0">
        <p
          className="text-sm truncate"
          style={{
            color: isDone ? "var(--text-muted)" : "var(--text-primary)",
            textDecoration: isDone ? "line-through" : "none",
          }}
        >
          {action.title}
        </p>
        <div className="flex items-center gap-2 text-micro" style={{ color: "var(--text-muted)" }}>
          {action.assignee && <span>{action.assignee.displayName}</span>}
          {action.dueDate && (
            <>
              <span>&middot;</span>
              <span
                style={{
                  color: isOverdue(action.dueDate) && !isDone ? "var(--error)" : "var(--text-muted)",
                }}
              >
                {action.dueDate}
              </span>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
