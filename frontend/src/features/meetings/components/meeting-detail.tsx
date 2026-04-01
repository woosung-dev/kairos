"use client";

import { useState } from "react";
import { MeetingSummary } from "./meeting-summary";
import { TranscriptViewer } from "./transcript-viewer";

const TABS = ["요약", "트랜스크립트"] as const;

interface MeetingDetailProps {
  meetingId: string;
}

export function MeetingDetail({ meetingId }: MeetingDetailProps) {
  const [activeTab, setActiveTab] = useState<(typeof TABS)[number]>("요약");

  return (
    <div className="p-6">
      {/* 메타데이터 */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <h1
            className="text-2xl font-bold"
            style={{ fontFamily: "var(--font-display)", color: "var(--text-primary)" }}
          >
            회의
          </h1>
          <span
            className="px-2 py-0.5 rounded-full text-xs"
            style={{
              background: "var(--surface-active)",
              color: "var(--text-muted)",
            }}
          >
            대기 중
          </span>
        </div>
        <p className="text-xs" style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
          ID: {meetingId}
        </p>
      </div>

      {/* 탭 */}
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

      {/* 탭 콘텐츠 */}
      {activeTab === "요약" && <MeetingSummary summary={null} />}
      {activeTab === "트랜스크립트" && <TranscriptViewer segments={null} />}
    </div>
  );
}
