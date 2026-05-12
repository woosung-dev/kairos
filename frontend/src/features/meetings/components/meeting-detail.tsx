"use client";

import { useState } from "react";
import { MeetingSummaryView } from "./meeting-summary-view";
import { TranscriptView } from "./transcript-view";
import { ActionView } from "./action-view";
import { MeetingExportButton } from "./export-button";
import { useMeetingDetail } from "../hooks";
import { useWorkspaceStore } from "@/features/workspaces/store";
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
    <div className="p-6 animate-pulse">
      <div className="mb-6">
        <div className="h-8 rounded w-2/3 mb-2" style={{ background: "var(--surface-active)" }} />
        <div className="h-4 rounded w-1/3" style={{ background: "var(--surface-active)" }} />
      </div>
      <div className="flex gap-4 mb-6 border-b" style={{ borderColor: "var(--border-subtle)" }}>
        {["요약", "트랜스크립트", "액션"].map((tab) => (
          <div key={tab} className="h-10 w-20 rounded" style={{ background: "var(--surface-active)" }} />
        ))}
      </div>
      <div className="space-y-3">
        <div className="h-24 rounded-lg" style={{ background: "var(--surface-active)" }} />
        <div className="h-32 rounded-lg" style={{ background: "var(--surface-active)" }} />
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

/* ── 컴포넌트 ── */

interface MeetingDetailProps {
  meetingId: string;
}

export function MeetingDetail({ meetingId }: MeetingDetailProps) {
  const [activeTab, setActiveTab] = useState<TabType>("요약");
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
          <MeetingExportButton meetingId={meetingId} meetingTitle={meeting.title} />
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
                className="px-2 py-0.5 rounded-full text-[11px]"
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

      {/* 처리 중 상태면 탭 대신 안내 메시지 */}
      {isProcessing ? (
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
    </div>
  );
}

