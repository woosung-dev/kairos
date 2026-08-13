// 프로젝트 대시보드 셸 — project/role 조회 + 다이얼로그 open 상태만 소유 (BL-AV-1 분해)
"use client";

import { useState } from "react";
import { AlertTriangle } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { useWorkspaceRole } from "@/features/members/hooks";
import { useWorkspaceStore } from "@/features/workspaces/store";
import { useProject } from "../../hooks";
import { ProjectMembersPanel } from "../project-members-panel";
import { DashboardContent } from "./dashboard-content";
import { DashboardHeader } from "./dashboard-header";
import { ProjectAdminDialogs } from "./project-admin-dialogs";

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

  const [visibilityDialogOpen, setVisibilityDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [archiveAlertOpen, setArchiveAlertOpen] = useState(false);
  const [deleteAlertOpen, setDeleteAlertOpen] = useState(false);
  const { canManage, isLoading: isRoleLoading } = useWorkspaceRole(wid);

  const { data: project, isLoading: projectLoading, error: projectError } = useProject(wid, projectId);

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

      {/* 본문 게이트는 가시 UI인 멤버 패널만 제어한다. */}
      <DashboardContent wid={wid} projectId={projectId}>
        {wid && (
          <ProjectMembersPanel
            workspaceId={wid}
            projectId={projectId}
            visibility={project.visibility}
            canManage={canManage}
          />
        )}
      </DashboardContent>

      <ProjectAdminDialogs
        wid={wid}
        projectId={projectId}
        project={project}
        visibilityDialogOpen={visibilityDialogOpen}
        onVisibilityDialogOpenChange={setVisibilityDialogOpen}
        editDialogOpen={editDialogOpen}
        onEditDialogOpenChange={setEditDialogOpen}
        archiveAlertOpen={archiveAlertOpen}
        onArchiveAlertOpenChange={setArchiveAlertOpen}
        deleteAlertOpen={deleteAlertOpen}
        onDeleteAlertOpenChange={setDeleteAlertOpen}
      />
    </div>
  );
}
