"use client";

import { useState, useRef, useEffect } from "react";
import { toast } from "sonner";
import { useMeetingDetail, useMeetingStatus } from "../hooks";
import { useWorkspaceStore } from "@/features/workspaces/store";
import {
  useAddMeetingProject,
  useRemoveMeetingProject,
} from "@/features/projects/hooks";
import { ProjectCombobox } from "@/features/projects/components/project-combobox";
import { MeetingSummary } from "./meeting-summary";
import { TranscriptViewer } from "./transcript-viewer";

const TABS = ["요약", "트랜스크립트"] as const;

const statusLabels: Record<string, string> = {
  uploading: "업로드 중",
  transcribing: "트랜스크립트 생성 중...",
  analyzing: "AI 분석 중...",
  embedding: "임베딩 중...",
  completed: "완료",
  failed: "실패",
};

const statusColors: Record<string, string> = {
  uploading: "var(--info)",
  transcribing: "var(--info)",
  analyzing: "var(--info)",
  embedding: "var(--info)",
  completed: "var(--success)",
  failed: "var(--error)",
};

interface MeetingDetailProps {
  meetingId: string;
}

export function MeetingDetail({ meetingId }: MeetingDetailProps) {
  const [activeTab, setActiveTab] = useState<(typeof TABS)[number]>("요약");
  const [isProjectComboboxOpen, setIsProjectComboboxOpen] = useState(false);
  const comboboxAnchorRef = useRef<HTMLDivElement>(null);
  const activeWorkspaceId = useWorkspaceStore((s) => s.activeWorkspaceId);

  const statusQuery = useMeetingStatus(activeWorkspaceId ?? undefined, meetingId);
  const detailQuery = useMeetingDetail(activeWorkspaceId ?? undefined, meetingId);
  const addProject = useAddMeetingProject(activeWorkspaceId ?? undefined);
  const removeProject = useRemoveMeetingProject(activeWorkspaceId ?? undefined);

  const status = statusQuery.data?.status ?? "uploading";
  const isProcessing = !["completed", "failed"].includes(status);
  const meeting = detailQuery.data;

  // 처리 완료 시 토스트
  const prevStatusRef = useRef(status);
  useEffect(() => {
    if (prevStatusRef.current !== "completed" && status === "completed") {
      toast.success("AI가 프로젝트에 연결했습니다");
    }
    prevStatusRef.current = status;
  }, [status]);

  function handleAddProject(projectId: string) {
    addProject.mutate(
      { meetingId, projectId },
      {
        onSuccess: () => toast.success("프로젝트가 연결되었습니다"),
        onError: (err: Error) => toast.error(err.message || "프로젝트 연결에 실패했습니다"),
      }
    );
    setIsProjectComboboxOpen(false);
  }

  function handleRemoveProject(projectId: string) {
    removeProject.mutate(
      { meetingId, projectId },
      {
        onSuccess: () => toast("프로젝트 연결이 해제되었습니다"),
        onError: (err: Error) => toast.error(err.message || "연결 해제에 실패했습니다"),
      }
    );
  }

  const linkedProjectIds = (meeting?.projects ?? []).map((p) => p.id);

  return (
    <div className="p-6">
      {/* 메타데이터 */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <h1
            className="text-2xl font-bold"
            style={{ fontFamily: "var(--font-display)", color: "var(--text-primary)" }}
          >
            {meeting?.title ?? "회의"}
          </h1>
          <span
            className="px-2 py-0.5 rounded-full text-xs font-medium"
            style={{
              background: isProcessing ? "var(--accent-subtle)" : status === "completed" ? "rgba(52,211,153,0.1)" : "rgba(248,113,113,0.1)",
              color: statusColors[status] ?? "var(--text-muted)",
            }}
          >
            {statusLabels[status] ?? status}
          </span>
        </div>
        {meeting?.durationSec && (
          <p className="text-xs" style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
            {Math.floor(meeting.durationSec / 60)}분 {meeting.durationSec % 60}초
          </p>
        )}
      </div>

      {/* 연결된 프로젝트 섹션 */}
      <div className="mb-6">
        <h2
          className="text-sm font-semibold mb-2"
          style={{ color: "var(--text-secondary)" }}
        >
          연결된 프로젝트
        </h2>
        <div className="flex flex-wrap items-center gap-2 relative" ref={comboboxAnchorRef}>
          {(meeting?.projects ?? []).map((project) => (
            <span
              key={project.id}
              className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium"
              style={{
                background: "var(--accent-subtle)",
                color: "var(--accent)",
                borderRadius: "var(--radius-sm)",
              }}
            >
              {project.title}
              <button
                onClick={() => handleRemoveProject(project.id)}
                className="ml-0.5 hover:opacity-70 transition-opacity"
                style={{ color: "var(--accent)" }}
                aria-label={`${project.title} 연결 해제`}
              >
                &times;
              </button>
            </span>
          ))}

          {(meeting?.projects ?? []).length === 0 && !isProjectComboboxOpen && (
            <span className="text-xs" style={{ color: "var(--text-muted)" }}>
              연결된 프로젝트가 없습니다
            </span>
          )}

          <button
            onClick={() => setIsProjectComboboxOpen(!isProjectComboboxOpen)}
            className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium border transition-colors"
            style={{
              borderColor: "var(--border)",
              color: "var(--text-muted)",
              borderRadius: "var(--radius-sm)",
            }}
          >
            + 추가
          </button>

          {isProjectComboboxOpen && (
            <div className="absolute top-full left-0 mt-1">
              <ProjectCombobox
                onSelect={handleAddProject}
                onClose={() => setIsProjectComboboxOpen(false)}
                excludeIds={linkedProjectIds}
              />
            </div>
          )}
        </div>
      </div>

      {/* 처리 중 표시 */}
      {isProcessing && (
        <div
          className="p-4 rounded mb-6 flex items-center gap-3"
          style={{
            background: "var(--accent-subtle)",
            borderRadius: "var(--radius-md)",
          }}
        >
          <span className="text-xl animate-spin">⏳</span>
          <div>
            <p className="text-sm font-medium" style={{ color: "var(--accent)" }}>
              {statusLabels[status]}
            </p>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              잠시만 기다려주세요. 3초마다 자동 갱신됩니다.
            </p>
          </div>
        </div>
      )}

      {/* 실패 표시 */}
      {status === "failed" && (
        <div
          className="p-4 rounded mb-6"
          style={{
            background: "rgba(248,113,113,0.1)",
            borderRadius: "var(--radius-md)",
          }}
        >
          <p className="text-sm font-medium" style={{ color: "var(--error)" }}>
            처리에 실패했습니다
          </p>
          {statusQuery.data?.errorMessage && (
            <p className="text-xs mt-1" style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
              {statusQuery.data.errorMessage}
            </p>
          )}
        </div>
      )}

      {/* 탭 (완료 시에만) */}
      {status === "completed" && (
        <>
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

          {activeTab === "요약" && <MeetingSummary summary={meeting?.summary ?? null} />}
          {activeTab === "트랜스크립트" && <TranscriptViewer segments={meeting?.transcript ?? null} />}
        </>
      )}
    </div>
  );
}
