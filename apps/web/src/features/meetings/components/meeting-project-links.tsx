// 회의 상세의 연결 프로젝트 — 칩 표시 + (member 이상) 연결·해제 (C-002)
//
// 이전엔 칩만 있었고 연결 경로가 UI 에 없었다. AI 가 "새 프로젝트" 를 제안한 회의는 인박스에서 확정해도
// 프로젝트가 없어 연결되지 않으므로, 회의 상세가 수동 연결의 유일한 자리다.
"use client";

import { useState } from "react";
import Link from "next/link";
import { Folder, Plus, X } from "lucide-react";
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
import { API_PAGE_SIZE_MAX } from "@/lib/api-client";
import {
  useAddMeetingProject,
  useProjects,
  useRemoveMeetingProject,
} from "@/features/projects/hooks";
import type { MeetingDetail } from "../types";

type LinkedProject = MeetingDetail["projects"][number];

/** 공개 범위를 넓히는 조작만 한 번 확인한다 */
type PendingConfirm = { kind: "link" | "unlink"; projectId: string; title: string };

interface MeetingProjectLinksProps {
  workspaceId: string | undefined;
  meetingId: string;
  /** BE 상세 응답의 연결 프로젝트 — 요청자가 볼 수 있는 것만 온다 */
  linkedProjects: LinkedProject[];
  /** member 이상 — 연결·해제 가능. viewer 는 읽기 전용 칩만 본다 */
  canEdit: boolean;
}

export function MeetingProjectLinks({
  workspaceId,
  meetingId,
  linkedProjects,
  canEdit,
}: MeetingProjectLinksProps) {
  const [isPickerOpen, setIsPickerOpen] = useState(false);
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [pendingConfirm, setPendingConfirm] = useState<PendingConfirm | null>(null);
  const addLink = useAddMeetingProject(workspaceId);
  const removeLink = useRemoveMeetingProject(workspaceId);

  // 후보 = 요청자가 볼 수 있는 진행 중 프로젝트 (BE 목록이 visibility 로 이미 거른다).
  // picker 를 열 때만 조회한다 — 인박스 picker·액션 보드와 같은 캐시 키(active·pageSize 100)를 공유.
  const candidatesQuery = useProjects(isPickerOpen ? workspaceId : undefined, {
    status: "active",
    pageSize: API_PAGE_SIZE_MAX,
  });
  const linkedIds = new Set(linkedProjects.map((project) => project.id));
  const candidates = (candidatesQuery.data?.items ?? []).filter(
    (project) => !linkedIds.has(project.id),
  );
  // 목록에 실제로 있는 옵션만 제출한다 — 숨은 값이 select 에 남은 채 전송되던 인박스 결함(codex P1)과 같은 구멍 방지
  const pickerProjectId = candidates.some((project) => project.id === selectedProjectId)
    ? selectedProjectId
    : "";
  const isBusy = addLink.isPending || removeLink.isPending;

  if (!canEdit && linkedProjects.length === 0) return null;

  function handleClosePicker() {
    setIsPickerOpen(false);
    setSelectedProjectId("");
  }

  // 회의 가시성 = 링크 0개면 워크스페이스 전체, 아니면 "볼 수 있는 링크가 하나라도 있으면" (OR).
  // 그래서 공개 범위가 넓어지는 조작은 두 가지뿐이다 (E-FE E-2):
  //  ① 공개 프로젝트가 하나도 없는 회의에 공개 프로젝트를 연결 (링크 0개 회의는 이미 전체 공개라 좁아진다)
  //  ② 마지막 링크를 해제 → 링크 0개 = 전체 공개. 다른 링크가 남는 해제는 좁아지기만 한다.
  // 요청자에게 안 보이는 링크는 상세 응답에 없어서 ②는 "보이는 링크 기준 마지막" 으로 판단한다.
  const hasPublicLink = linkedProjects.some((project) => project.visibility === "public");

  function handleLink() {
    if (!pickerProjectId) return;
    const target = candidates.find((project) => project.id === pickerProjectId);
    if (target?.visibility === "public" && linkedProjects.length > 0 && !hasPublicLink) {
      setPendingConfirm({ kind: "link", projectId: target.id, title: target.title });
      return;
    }
    addLink.mutate({ meetingId, projectId: pickerProjectId }, { onSuccess: handleClosePicker });
  }

  function handleUnlink(project: LinkedProject) {
    if (linkedProjects.length === 1) {
      setPendingConfirm({ kind: "unlink", projectId: project.id, title: project.title });
      return;
    }
    removeLink.mutate({ meetingId, projectId: project.id });
  }

  function handleConfirm() {
    if (!pendingConfirm) return;
    const done = { onSettled: () => setPendingConfirm(null) };
    if (pendingConfirm.kind === "link") {
      addLink.mutate(
        { meetingId, projectId: pendingConfirm.projectId },
        { onSuccess: handleClosePicker, ...done },
      );
    } else {
      removeLink.mutate({ meetingId, projectId: pendingConfirm.projectId }, done);
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-1.5 mt-3" data-testid="meeting-linked-projects">
      {linkedProjects.map((project) => (
        <span
          key={project.id}
          className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-micro font-medium"
          style={{
            background: "var(--accent-subtle)",
            color: "var(--accent)",
            borderRadius: "var(--radius-sm)",
          }}
        >
          <Link
            href={`/projects/${project.id}`}
            className="inline-flex items-center gap-1 transition-colors hover:opacity-80"
          >
            <Folder size={11} />
            {project.title}
          </Link>
          {canEdit && (
            <button
              type="button"
              onClick={() => handleUnlink(project)}
              disabled={isBusy}
              aria-label={`${project.title} 연결 해제`}
              data-testid="meeting-project-unlink"
              className="inline-flex items-center justify-center w-4 h-4 -mr-1 rounded transition-colors hover:opacity-70 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            >
              <X size={11} />
            </button>
          )}
        </span>
      ))}

      {canEdit && !isPickerOpen && (
        <button
          type="button"
          onClick={() => setIsPickerOpen(true)}
          data-testid="meeting-project-link-open"
          className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-micro font-medium border transition-colors cursor-pointer hover:bg-[var(--surface-active)]"
          style={{
            borderColor: "var(--border)",
            color: "var(--text-secondary)",
            borderRadius: "var(--radius-sm)",
          }}
        >
          <Plus size={11} />
          프로젝트 연결
        </button>
      )}

      {canEdit && isPickerOpen && (
        <div className="flex flex-wrap items-center gap-1.5" data-testid="meeting-project-picker">
          {candidatesQuery.isLoading ? (
            <span className="text-xs" style={{ color: "var(--text-muted)" }}>
              프로젝트 목록을 불러오는 중…
            </span>
          ) : candidatesQuery.isError ? (
            <span className="text-xs" style={{ color: "var(--text-muted)" }}>
              프로젝트 목록을 불러올 수 없습니다.
            </span>
          ) : candidates.length === 0 ? (
            <span className="text-xs" style={{ color: "var(--text-muted)" }}>
              연결할 수 있는 진행 중 프로젝트가 없습니다.
            </span>
          ) : (
            <select
              value={pickerProjectId}
              onChange={(event) => setSelectedProjectId(event.target.value)}
              aria-label="연결할 프로젝트"
              data-testid="meeting-project-select"
              className="px-2 py-1 rounded border text-xs bg-transparent outline-none"
              style={{
                borderColor: "var(--border)",
                color: "var(--text-primary)",
                borderRadius: "var(--radius-sm)",
              }}
            >
              <option value="">프로젝트 선택...</option>
              {candidates.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.title}
                </option>
              ))}
            </select>
          )}
          <button
            type="button"
            onClick={handleLink}
            disabled={!pickerProjectId || isBusy}
            data-testid="meeting-project-link-submit"
            className="px-2 py-1 rounded text-xs font-medium transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            style={{
              background: "var(--accent)",
              color: "var(--background)",
              borderRadius: "var(--radius-sm)",
            }}
          >
            {addLink.isPending ? "연결 중…" : "연결"}
          </button>
          <button
            type="button"
            onClick={handleClosePicker}
            className="px-2 py-1 text-xs cursor-pointer"
            style={{ color: "var(--text-muted)" }}
          >
            취소
          </button>
        </div>
      )}

      <AlertDialog
        open={pendingConfirm !== null}
        onOpenChange={(open) => {
          if (!open) setPendingConfirm(null);
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {pendingConfirm?.kind === "link" ? "공개 프로젝트에 연결할까요?" : "마지막 연결을 해제할까요?"}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {pendingConfirm?.kind === "link"
                ? `“${pendingConfirm.title}” 은(는) 공개 프로젝트입니다. 연결하면 이 회의를 워크스페이스 멤버 전원이 볼 수 있습니다.`
                : `“${pendingConfirm?.title ?? ""}” 연결을 해제하면 이 회의가 어떤 프로젝트에도 속하지 않아 워크스페이스 멤버 전원에게 보일 수 있습니다.`}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>취소</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirm}
              disabled={addLink.isPending || removeLink.isPending}
              data-testid={
                pendingConfirm?.kind === "link"
                  ? "meeting-project-link-confirm"
                  : "meeting-project-unlink-confirm"
              }
            >
              {pendingConfirm?.kind === "link" ? "연결" : "연결 해제"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
