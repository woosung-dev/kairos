"use client";

import { useState } from "react";
import { ArrowUpRight } from "lucide-react";
import { MeetingSummaryView } from "./meeting-summary-view";
import { TranscriptView } from "./transcript-view";
import { ActionView } from "./action-view";
import { MeetingExportButton } from "./export-button";
import { useMeetingDetail } from "../hooks";
import { useWorkspaceStore } from "@/features/workspaces/store";
import { ItemPromoteModal } from "@/components/shared/ItemPromoteModal";
import { Skeleton } from "@/components/ui/skeleton";
import type { MeetingStatus } from "../types";

/* ── 3뷰 탭 ── */

const TABS = ["요약", "트랜스크립트", "액션"] as const;
type TabType = (typeof TABS)[number];

/* ── 상태 라벨 ── */

const STATUS_LABELS: Record<MeetingStatus, string> = {
  uploading: "업로드 중",
  transcribing: "STT 처리 중",
  analyzing: "AI 분석 중",
  embedding: "임베딩 중",
  completed: "완료",
  failed: "실패",
};

const STATUS_COLORS: Record<MeetingStatus, { background: string; color: string }> = {
  uploading: { background: "rgba(251,191,36,0.1)", color: "var(--warning)" },
  transcribing: { background: "rgba(251,191,36,0.1)", color: "var(--warning)" },
  analyzing: { background: "rgba(251,191,36,0.1)", color: "var(--warning)" },
  embedding: { background: "rgba(251,191,36,0.1)", color: "var(--warning)" },
  completed: { background: "rgba(52,211,153,0.1)", color: "var(--success)" },
  failed: { background: "rgba(239,68,68,0.1)", color: "var(--error)" },
};

/* ── 로딩 스켈레톤 ── */

function MeetingDetailSkeleton() {
  return (
    <div className="p-6">
      <div className="mb-6">
        <Skeleton className="h-8 rounded w-2/3 mb-2" />
        <Skeleton className="h-4 rounded w-1/3" />
      </div>
      <div className="flex gap-4 mb-6 border-b" style={{ borderColor: "var(--border-subtle)" }}>
        {["요약", "트랜스크립트", "액션"].map((tab) => (
          <Skeleton key={tab} className="h-10 w-20 rounded" />
        ))}
      </div>
      <div className="space-y-3">
        <Skeleton className="h-24 rounded-lg" />
        <Skeleton className="h-32 rounded-lg" />
      </div>
    </div>
  );
}

/* ── 처리 중 안내 ── */

function ProcessingView({ status }: { status: MeetingStatus }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <span className="text-4xl mb-4">⚙️</span>
      <h3
        className="text-lg font-semibold mb-2"
        style={{ color: "var(--text-primary)", fontFamily: "var(--font-display)" }}
      >
        {STATUS_LABELS[status]}
      </h3>
      <p className="text-sm" style={{ color: "var(--text-muted)" }}>
        처리가 완료되면 자동으로 업데이트됩니다
      </p>
    </div>
  );
}

/* ── 실패 안내 (S28b BUG-MEETING-FAILED-UI) ── */

function FailedMeetingView() {
  // 사용자에겐 친화적 메시지만 노출 — 원시 error_message(서명 URL 포함 httpx 오류 등)는
  // 상세 응답(errorMessage)에 남겨 support/디버깅용으로 두되 UI 에 raw 로 덤프하지 않음.
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <span className="text-4xl mb-4">⚠️</span>
      <h3
        className="text-lg font-semibold mb-2"
        style={{ color: "var(--text-primary)", fontFamily: "var(--font-display)" }}
      >
        분석에 실패했습니다
      </h3>
      <p className="text-sm mb-4 max-w-md" style={{ color: "var(--text-muted)" }}>
        처리 중 오류가 발생했습니다. 파일 형식과 크기를 확인하고 다시 업로드해 주세요.
      </p>
      <a
        href="/new"
        className="px-4 py-2 rounded text-sm font-medium"
        style={{
          background: "var(--accent)",
          color: "var(--background)",
          borderRadius: "var(--radius-sm)",
        }}
      >
        다시 업로드
      </a>
    </div>
  );
}

/* ── 컴포넌트 ── */

interface MeetingDetailProps {
  meetingId: string;
}

export function MeetingDetail({ meetingId }: MeetingDetailProps) {
  const [activeTab, setActiveTab] = useState<TabType>("요약");
  const [isPromoteOpen, setIsPromoteOpen] = useState(false);
  const activeWorkspaceId = useWorkspaceStore((s) => s.activeWorkspaceId);

  const { data: meeting, isLoading, error } = useMeetingDetail(
    activeWorkspaceId ?? undefined,
    meetingId
  );

  function handleSwitchToTranscript() {
    setActiveTab("트랜스크립트");
  }

  /* 로딩 */
  if (isLoading) return <MeetingDetailSkeleton />;

  /* 에러 */
  if (error || !meeting) {
    return (
      <div className="p-6 flex flex-col items-center justify-center py-20 text-center">
        <span className="text-4xl mb-4">⚠️</span>
        <p className="text-sm" style={{ color: "var(--error)" }}>
          회의 데이터를 불러올 수 없습니다. 잠시 후 다시 시도해주세요.
        </p>
      </div>
    );
  }

  /* 처리 중 상태 */
  const isProcessing = meeting.status !== "completed" && meeting.status !== "failed";

  /* 날짜 포맷 */
  const displayDate = meeting.recordedAt
    ? new Date(meeting.recordedAt).toLocaleDateString("ko-KR")
    : new Date(meeting.createdAt).toLocaleDateString("ko-KR");

  /* 참석자: transcript에서 고유 화자 추출 */
  const speakers = meeting.transcript
    ? [...new Set(meeting.transcript.map((seg) => seg.speaker))]
    : [];

  /* 소요시간 (초 → 분) */
  const durationMin = meeting.durationSec !== null
    ? Math.round(meeting.durationSec / 60)
    : null;

  const statusStyle = STATUS_COLORS[meeting.status];

  return (
    <div className="p-6">
      {/* 회의 메타데이터 */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <h1
            className="text-2xl font-bold"
            style={{ fontFamily: "var(--font-display)", color: "var(--text-primary)" }}
          >
            {meeting.title}
          </h1>
          <span
            data-testid="meeting-status"
            className="px-2 py-0.5 rounded-full text-xs font-medium"
            style={{
              background: statusStyle.background,
              color: statusStyle.color,
            }}
          >
            {STATUS_LABELS[meeting.status]}
          </span>
          {/* S28b OBS-MEETING-ACTIONS: export 는 완료 상태에서만 (빈/실패 export 방지) */}
          {meeting.status === "completed" && (
            <MeetingExportButton meetingId={meetingId} meetingTitle={meeting.title} />
          )}
          {/* Sprint 23 D4: 워크스페이스 이동 (promote 1-button) */}
          <button
            type="button"
            onClick={() => setIsPromoteOpen(true)}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium transition-colors border"
            style={{
              borderColor: "var(--border)",
              color: "var(--text-secondary)",
              borderRadius: "var(--radius-sm)",
              cursor: "pointer",
              minHeight: "32px",
            }}
            aria-label="워크스페이스 이동"
          >
            <ArrowUpRight className="h-3.5 w-3.5" />
            워크스페이스 이동
          </button>
        </div>

        {/* 메타 정보 */}
        <div className="flex items-center gap-4 text-xs" style={{ color: "var(--text-muted)" }}>
          {durationMin !== null && (
            <>
              <span style={{ fontFamily: "var(--font-mono)" }}>{durationMin}분</span>
              <span>&middot;</span>
            </>
          )}
          {speakers.length > 0 && (
            <>
              <span>참석자 {speakers.length}명</span>
              <span>&middot;</span>
            </>
          )}
          <span>{displayDate}</span>
        </div>

        {/* 참석자 */}
        {speakers.length > 0 && (
          <div className="flex items-center gap-2 mt-2">
            {speakers.map((speaker) => (
              <span
                key={speaker}
                className="px-2 py-0.5 rounded-full text-caption"
                style={{
                  background: "var(--surface-active)",
                  color: "var(--text-secondary)",
                }}
              >
                {speaker}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* 상태별 본문: 실패 / 처리중 / 완료 탭 (S28b BUG-MEETING-FAILED-UI) */}
      {meeting.status === "failed" ? (
        <FailedMeetingView />
      ) : isProcessing ? (
        <ProcessingView status={meeting.status} />
      ) : (
        <>
          {/* 3뷰 탭 네비게이션 */}
          <div
            className="flex items-center gap-1 mb-6 border-b"
            style={{ borderColor: "var(--border-subtle)" }}
          >
            {TABS.map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className="px-3 py-2 text-sm font-medium transition-colors"
                style={{
                  color: activeTab === tab ? "var(--accent)" : "var(--text-muted)",
                  borderBottom: activeTab === tab ? "2px solid var(--accent)" : "2px solid transparent",
                  cursor: "pointer",
                  minHeight: "44px",
                }}
              >
                {tab}
              </button>
            ))}
          </div>

          {/* 탭 콘텐츠 */}
          {activeTab === "요약" && (
            <div data-testid="meeting-summary">
              <MeetingSummaryView
                summary={meeting.summary}
                onSwitchToTranscript={handleSwitchToTranscript}
              />
            </div>
          )}
          {activeTab === "트랜스크립트" && (
            <TranscriptView transcript={meeting.transcript} />
          )}
          {activeTab === "액션" && (
            <ActionView meetingId={meetingId} />
          )}
        </>
      )}

      {/* Sprint 23 D4: 워크스페이스 이동 modal */}
      {activeWorkspaceId && (
        <ItemPromoteModal
          itemType="meeting"
          itemId={meetingId}
          sourceWorkspaceId={activeWorkspaceId}
          open={isPromoteOpen}
          onOpenChange={setIsPromoteOpen}
        />
      )}
    </div>
  );
}

