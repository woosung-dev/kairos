// 프로젝트 대시보드 셸 — project/role 조회 + 다이얼로그 open 상태만 소유 (BL-AV-1 분해)
"use client";

import { useState } from "react";
import Link from "next/link";
import { AlertTriangle, FolderX } from "lucide-react";
import { ApiError } from "@/lib/api-client";
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

  /* 에러 — 404(삭제됨/접근 불가: BE 는 비-멤버의 private·draft 도 404 로 감춘다)와 그 외를 구분한다.
     이전엔 둘 다 "불러올 수 없습니다" 였고 돌아갈 길이 없었다. */
  if (projectError || !project) {
    const isNotFound = projectError instanceof ApiError && projectError.status === 404;
    return (
      <div className="p-6 flex flex-col items-center justify-center py-20 text-center">
        {isNotFound ? (
          <FolderX className="w-10 h-10 mb-4" style={{ color: "var(--text-muted)" }} />
        ) : (
          <AlertTriangle className="w-10 h-10 mb-4" style={{ color: "var(--error)" }} />
        )}
        <h2
          className="text-lg font-semibold mb-2"
          style={{ color: "var(--text-primary)", fontFamily: "var(--font-display)" }}
        >
          {isNotFound ? "프로젝트를 찾을 수 없습니다" : "프로젝트를 불러올 수 없습니다"}
        </h2>
        <p className="text-sm mb-6 max-w-md" style={{ color: "var(--text-muted)" }}>
          {isNotFound
            ? "삭제되었거나 접근 권한이 없는 프로젝트입니다. 비공개·작업 중 프로젝트는 멤버에게만 보입니다."
            : "잠시 후 다시 시도해주세요."}
        </p>
        <Link
          href="/projects"
          className="px-4 py-2 rounded text-sm font-medium"
          style={{
            background: "var(--surface-active)",
            color: "var(--text-primary)",
            borderRadius: "var(--radius-sm)",
          }}
        >
          프로젝트 목록으로
        </Link>
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

      <DashboardContent wid={wid} projectId={projectId} />

      {/* 멤버 패널은 콘텐츠 유무와 무관하게 렌더한다 — 이전엔 DashboardContent 의 children 이라
          콘텐츠 0 인 비공개 프로젝트에서 온보딩 뷰에 가려져 owner 가 멤버를 추가할 방법이 없었다.
          (비공개가 아니면 패널 자체가 null 을 반환한다.) */}
      {wid && (
        <ProjectMembersPanel
          workspaceId={wid}
          projectId={projectId}
          visibility={project.visibility}
          canManage={canManage}
        />
      )}

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
