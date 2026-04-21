"use client";

import { useState, useMemo } from "react";
import type { TranscriptSegment } from "../types";

/* ── 유틸리티 ── */

/** startSec → "MM:SS" 형식 변환 */
function formatTimestamp(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

/* ── Props ── */

interface TranscriptViewProps {
  transcript: TranscriptSegment[] | null;
}

/* ── 컴포넌트 ── */

export function TranscriptView({ transcript }: TranscriptViewProps) {
  const [searchQuery, setSearchQuery] = useState("");

  /* 트랜스크립트 없음 */
  if (!transcript || transcript.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <span className="text-4xl mb-4">📝</span>
        <h3
          className="text-lg font-semibold mb-2"
          style={{ color: "var(--text-primary)", fontFamily: "var(--font-display)" }}
        >
          트랜스크립트가 없습니다
        </h3>
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          STT 처리가 완료되면 자동으로 생성됩니다
        </p>
      </div>
    );
  }

  return <TranscriptContent transcript={transcript} searchQuery={searchQuery} onSearchChange={setSearchQuery} />;
}

/* ── 내부 컨텐츠 컴포넌트 ── */

interface TranscriptContentProps {
  transcript: TranscriptSegment[];
  searchQuery: string;
  onSearchChange: (v: string) => void;
}

function TranscriptContent({ transcript, searchQuery, onSearchChange }: TranscriptContentProps) {
  const filteredTranscript = useMemo(() => {
    if (!searchQuery.trim()) return transcript;
    const q = searchQuery.toLowerCase();
    return transcript.filter(
      (seg) =>
        seg.text.toLowerCase().includes(q) ||
        seg.speaker.toLowerCase().includes(q)
    );
  }, [transcript, searchQuery]);

  return (
    <div className="space-y-4">
      {/* 검색 입력 */}
      <div className="relative">
        <input
          type="text"
          placeholder="트랜스크립트 검색..."
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          className="w-full px-3 py-2 pl-8 rounded border text-sm bg-transparent outline-none"
          style={{
            borderColor: "var(--border)",
            color: "var(--text-primary)",
            borderRadius: "var(--radius-sm)",
          }}
        />
        <span
          className="absolute left-2.5 top-1/2 -translate-y-1/2 text-xs"
          style={{ color: "var(--text-muted)" }}
        >
          🔍
        </span>
      </div>

      {/* 결과 수 */}
      {searchQuery.trim() && (
        <p className="text-xs" style={{ color: "var(--text-muted)" }}>
          {filteredTranscript.length}건 검색됨
        </p>
      )}

      {/* 트랜스크립트 리스트 */}
      <div className="space-y-3">
        {filteredTranscript.map((seg, idx) => (
          <TranscriptSegmentRow
            key={`${seg.speaker}-${seg.startSec}-${idx}`}
            segment={seg}
            searchQuery={searchQuery}
          />
        ))}
      </div>

      {filteredTranscript.length === 0 && (
        <div className="text-center py-8">
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            검색 결과가 없습니다
          </p>
        </div>
      )}
    </div>
  );
}

/* ── 세그먼트 행 ── */

function TranscriptSegmentRow({
  segment,
  searchQuery,
}: {
  segment: TranscriptSegment;
  searchQuery: string;
}) {
  const timestamp = formatTimestamp(segment.startSec);

  return (
    <div
      className="flex gap-3 px-3 py-2 rounded-lg transition-colors"
      style={{
        background: "transparent",
        borderRadius: "var(--radius-lg)",
      }}
    >
      {/* 타임스탬프 */}
      <span
        className="shrink-0 text-xs pt-0.5"
        style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)", width: "44px" }}
      >
        {timestamp}
      </span>

      {/* 화자 + 텍스트 */}
      <div className="flex-1 min-w-0">
        <span className="text-xs font-medium mr-2" style={{ color: "var(--accent)" }}>
          {segment.speaker}
        </span>
        <span className="text-sm" style={{ color: "var(--text-secondary)" }}>
          {highlightText(segment.text, searchQuery)}
        </span>
      </div>
    </div>
  );
}

/** 검색어 하이라이트 헬퍼 */
function highlightText(text: string, query: string): React.ReactNode {
  if (!query.trim()) return text;

  const regex = new RegExp(`(${escapeRegex(query)})`, "gi");
  const parts = text.split(regex);

  return (
    <>
      {parts.map((part, i) =>
        regex.test(part) ? (
          <mark
            key={i}
            style={{
              background: "var(--accent-subtle)",
              color: "var(--accent)",
              borderRadius: "2px",
              padding: "0 2px",
            }}
          >
            {part}
          </mark>
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </>
  );
}

function escapeRegex(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
