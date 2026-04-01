"use client";

import type { TranscriptSegment } from "../types";
import { EmptyState } from "@/components/empty-state";

interface TranscriptViewerProps {
  segments: TranscriptSegment[] | null;
}

function formatTime(sec: number): string {
  const min = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${min.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}

export function TranscriptViewer({ segments }: TranscriptViewerProps) {
  if (!segments || segments.length === 0) {
    return (
      <EmptyState
        icon="🎙️"
        title="트랜스크립트가 아직 없습니다"
        description="음성 인식이 완료되면 화자별 트랜스크립트가 표시됩니다"
      />
    );
  }

  return (
    <div className="space-y-3">
      {segments.map((segment, i) => (
        <div key={i} className="flex gap-3">
          {/* 타임스탬프 */}
          <span
            className="shrink-0 text-xs pt-0.5"
            style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)", width: "44px" }}
          >
            {formatTime(segment.startSec)}
          </span>

          {/* 화자 + 텍스트 */}
          <div className="flex-1">
            <span
              className="text-xs font-medium mr-2"
              style={{ color: "var(--accent)" }}
            >
              {segment.speaker}
            </span>
            <span className="text-sm" style={{ color: "var(--text-secondary)" }}>
              {segment.text}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}
