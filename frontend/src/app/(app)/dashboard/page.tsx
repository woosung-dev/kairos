"use client";

import { useState } from "react";
import { useWorkspaces, useCreateWorkspace } from "@/features/workspaces/hooks";
import { useWorkspaceStore } from "@/features/workspaces/store";
import { useMeetings } from "@/features/meetings/hooks";
import { EmptyState } from "@/components/empty-state";
import Link from "next/link";
import type { Meeting } from "@/features/meetings/types";

// 워크스페이스 생성 다이얼로그
function CreateWorkspaceDialog({
  isOpen,
  onClose,
}: {
  isOpen: boolean;
  onClose: () => void;
}) {
  const [name, setName] = useState("");
  const createWorkspace = useCreateWorkspace();
  const setActiveWorkspaceId = useWorkspaceStore((s) => s.setActiveWorkspaceId);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    const ws = await createWorkspace.mutateAsync(name.trim());
    setActiveWorkspaceId(ws.id);
    setName("");
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* 오버레이 */}
      <div
        className="absolute inset-0"
        style={{ background: "rgba(0,0,0,0.5)" }}
        onClick={onClose}
      />
      {/* 다이얼로그 */}
      <div
        className="relative z-10 w-full max-w-md p-6 rounded-lg border"
        style={{
          background: "var(--surface)",
          borderColor: "var(--border)",
          borderRadius: "var(--radius-lg)",
        }}
      >
        <h2
          className="text-lg font-bold mb-4"
          style={{ fontFamily: "var(--font-display)", color: "var(--text-primary)" }}
        >
          워크스페이스 만들기
        </h2>
        <form onSubmit={handleSubmit}>
          <label
            className="block text-xs mb-1"
            style={{ color: "var(--text-secondary)" }}
          >
            워크스페이스 이름
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="예: 우리팀"
            autoFocus
            className="w-full px-3 py-2 rounded border text-sm bg-transparent outline-none mb-4"
            style={{
              borderColor: "var(--border)",
              color: "var(--text-primary)",
              borderRadius: "var(--radius-sm)",
            }}
          />
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded text-sm"
              style={{
                color: "var(--text-secondary)",
                borderRadius: "var(--radius-sm)",
              }}
            >
              취소
            </button>
            <button
              type="submit"
              disabled={!name.trim() || createWorkspace.isPending}
              className="px-4 py-2 rounded text-sm font-medium disabled:opacity-50"
              style={{
                background: "var(--accent)",
                color: "var(--background)",
                borderRadius: "var(--radius-sm)",
              }}
            >
              {createWorkspace.isPending ? "생성 중..." : "만들기"}
            </button>
          </div>
          {createWorkspace.isError && (
            <p className="text-xs mt-2" style={{ color: "var(--destructive)" }}>
              {createWorkspace.error.message}
            </p>
          )}
        </form>
      </div>
    </div>
  );
}

// 회의 카드
function MeetingCard({ meeting }: { meeting: Meeting }) {
  const statusLabels: Record<string, string> = {
    uploading: "업로드 중",
    transcribing: "트랜스크립트 생성 중",
    analyzing: "AI 분석 중",
    embedding: "임베딩 중",
    completed: "완료",
    failed: "실패",
  };

  return (
    <Link
      href={`/meetings/${meeting.id}`}
      className="block p-4 rounded border transition-colors hover:border-[var(--accent)]"
      style={{
        background: "var(--surface)",
        borderColor: "var(--border-subtle)",
        borderRadius: "var(--radius-md)",
      }}
    >
      <div className="flex items-center justify-between mb-2">
        <h3
          className="text-sm font-semibold truncate"
          style={{ color: "var(--text-primary)" }}
        >
          {meeting.title}
        </h3>
        <span
          className="shrink-0 px-2 py-0.5 rounded-full text-[10px]"
          style={{
            background:
              meeting.status === "completed"
                ? "var(--success-bg, rgba(34,197,94,0.1))"
                : meeting.status === "failed"
                  ? "var(--destructive-bg, rgba(239,68,68,0.1))"
                  : "var(--surface-active)",
            color:
              meeting.status === "completed"
                ? "var(--success, #22c55e)"
                : meeting.status === "failed"
                  ? "var(--destructive, #ef4444)"
                  : "var(--text-muted)",
          }}
        >
          {statusLabels[meeting.status] ?? meeting.status}
        </span>
      </div>
      <p className="text-xs" style={{ color: "var(--text-muted)" }}>
        {meeting.createdBy.displayName} &middot;{" "}
        {new Date(meeting.createdAt).toLocaleDateString("ko-KR")}
      </p>
    </Link>
  );
}

export default function DashboardPage() {
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  const { data: workspaces, isLoading: isLoadingWs } = useWorkspaces();
  const { activeWorkspaceId, setActiveWorkspaceId } = useWorkspaceStore();

  // 워크스페이스가 있고 active가 없으면 첫 번째를 선택
  const hasWorkspaces = workspaces && workspaces.length > 0;
  const currentWid =
    activeWorkspaceId && workspaces?.find((w) => w.id === activeWorkspaceId)
      ? activeWorkspaceId
      : workspaces?.[0]?.id;

  // active 동기화
  if (currentWid && currentWid !== activeWorkspaceId) {
    setActiveWorkspaceId(currentWid);
  }

  const { data: meetingsData, isLoading: isLoadingMeetings } = useMeetings(
    currentWid ?? undefined
  );

  // 로딩 상태
  if (isLoadingWs) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          로딩 중...
        </p>
      </div>
    );
  }

  // 워크스페이스 없음
  if (!hasWorkspaces) {
    return (
      <div className="p-6">
        <EmptyState
          icon="🏢"
          title="워크스페이스를 만들어주세요"
          description="워크스페이스를 만들면 회의 녹음, 프로젝트 관리를 시작할 수 있습니다"
        />
        <div className="flex justify-center mt-4">
          <button
            onClick={() => setIsDialogOpen(true)}
            className="px-4 py-2 rounded text-sm font-medium"
            style={{
              background: "var(--accent)",
              color: "var(--background)",
              borderRadius: "var(--radius-sm)",
            }}
          >
            워크스페이스 만들기
          </button>
        </div>
        <CreateWorkspaceDialog
          isOpen={isDialogOpen}
          onClose={() => setIsDialogOpen(false)}
        />
      </div>
    );
  }

  const meetings = meetingsData?.items ?? [];

  return (
    <div className="p-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1
            className="text-2xl font-bold mb-1"
            style={{
              fontFamily: "var(--font-display)",
              color: "var(--text-primary)",
            }}
          >
            대시보드
          </h1>
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            {workspaces?.find((w) => w.id === currentWid)?.name ?? ""}
          </p>
        </div>
        <Link
          href="/new"
          className="px-4 py-2 rounded text-sm font-medium"
          style={{
            background: "var(--accent)",
            color: "var(--background)",
            borderRadius: "var(--radius-sm)",
          }}
        >
          콘텐츠 추가
        </Link>
      </div>

      {/* 최근 회의 */}
      <div>
        <h2
          className="text-sm font-semibold mb-4 uppercase tracking-wider"
          style={{
            color: "var(--text-muted)",
            fontFamily: "var(--font-display)",
          }}
        >
          최근 회의
        </h2>

        {isLoadingMeetings ? (
          <p className="text-sm py-8 text-center" style={{ color: "var(--text-muted)" }}>
            로딩 중...
          </p>
        ) : meetings.length === 0 ? (
          <EmptyState
            icon="🎙️"
            title="아직 회의가 없습니다"
            description="회의를 녹음하면 AI가 자동으로 요약합니다"
            action={{ label: "회의 녹음 추가", href: "/new" }}
          />
        ) : (
          <div className="grid gap-3">
            {meetings.map((meeting) => (
              <MeetingCard key={meeting.id} meeting={meeting} />
            ))}
          </div>
        )}
      </div>

      <CreateWorkspaceDialog
        isOpen={isDialogOpen}
        onClose={() => setIsDialogOpen(false)}
      />
    </div>
  );
}
