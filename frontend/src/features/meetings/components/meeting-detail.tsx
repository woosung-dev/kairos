"use client";

import { useState } from "react";
import { useMeetingDetail, useMeetingStatus } from "../hooks";
import { useWorkspaceStore } from "@/features/workspaces/store";
import { MeetingSummary } from "./meeting-summary";
import { TranscriptViewer } from "./transcript-viewer";

const TABS = ["요약", "트랜스크립트"] as const;

const statusLabels: Record<string, string> = {
  uploading: "업로드 중",
  transcribing: "트랜스크립트 생성 중...",
  summarizing: "AI 요약 생성 중...",
  analyzing: "분석 중...",
  embedding: "임베딩 중...",
  completed: "완료",
  failed: "실패",
};

const statusColors: Record<string, string> = {
  uploading: "var(--info)",
  transcribing: "var(--info)",
  summarizing: "var(--info)",
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
  const activeWorkspaceId = useWorkspaceStore((s) => s.activeWorkspaceId);

  const statusQuery = useMeetingStatus(activeWorkspaceId ?? undefined, meetingId);
  const detailQuery = useMeetingDetail(activeWorkspaceId ?? undefined, meetingId);

  const status = statusQuery.data?.status ?? "uploading";
  const isProcessing = !["completed", "failed"].includes(status);
  const meeting = detailQuery.data;

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
