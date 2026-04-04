"use client";

import { useState } from "react";
import { MeetingSummaryView } from "./meeting-summary-view";
import { TranscriptView } from "./transcript-view";
import { ActionView } from "./action-view";
import { MeetingExportButton } from "./export-button";

/* ── Mock 데이터 ── */

const MOCK_MEETING = {
  id: "meeting-001",
  title: "Q2 제품 로드맵 전략 회의",
  date: "2026-03-31",
  durationMin: 32,
  participants: ["김민수", "이지은", "박현우", "최수진"],
  status: "completed" as const,
};

/* ── 3뷰 탭 ── */

const TABS = ["요약", "트랜스크립트", "액션"] as const;
type TabType = (typeof TABS)[number];

/* ── 컴포넌트 ── */

interface MeetingDetailProps {
  meetingId: string;
}

export function MeetingDetail({ meetingId }: MeetingDetailProps) {
  const [activeTab, setActiveTab] = useState<TabType>("요약");

  /* Mock 기반이므로 meetingId는 향후 API 연동 시 활용 */
  void meetingId;

  const meeting = MOCK_MEETING;

  function handleSwitchToTranscript() {
    setActiveTab("트랜스크립트");
  }

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
            className="px-2 py-0.5 rounded-full text-xs font-medium"
            style={{
              background: "rgba(52,211,153,0.1)",
              color: "var(--success)",
            }}
          >
            완료
          </span>
          <MeetingExportButton meetingId={meetingId} meetingTitle={meeting.title} />
        </div>

        {/* 메타 정보 */}
        <div className="flex items-center gap-4 text-xs" style={{ color: "var(--text-muted)" }}>
          <span style={{ fontFamily: "var(--font-mono)" }}>{meeting.durationMin}분</span>
          <span>&middot;</span>
          <span>참석자 {meeting.participants.length}명</span>
          <span>&middot;</span>
          <span>{meeting.date}</span>
        </div>

        {/* 참석자 */}
        <div className="flex items-center gap-2 mt-2">
          {meeting.participants.map((p) => (
            <span
              key={p}
              className="px-2 py-0.5 rounded-full text-[11px]"
              style={{
                background: "var(--surface-active)",
                color: "var(--text-secondary)",
              }}
            >
              {p}
            </span>
          ))}
        </div>
      </div>

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
        <MeetingSummaryView onSwitchToTranscript={handleSwitchToTranscript} />
      )}
      {activeTab === "트랜스크립트" && <TranscriptView />}
      {activeTab === "액션" && <ActionView />}
    </div>
  );
}
