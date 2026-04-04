"use client";

import { useState } from "react";

/* ── 출처 색상 시스템 ── */

interface SourceStyle {
  background: string;
  color: string;
}

const SOURCE_STYLES: Record<number, SourceStyle> = {
  1: { background: "var(--accent-subtle)", color: "var(--accent)" },
  2: { background: "rgba(167,139,250,0.1)", color: "#A78BFA" },
  3: { background: "rgba(251,191,36,0.1)", color: "#FBBF24" },
};

/* ── Mock 타입 ── */

interface SourceSnippet {
  id: number;
  speaker: string;
  timestamp: string;
  text: string;
}

interface SummaryBlock {
  label: string;
  content: string;
  /** 출처 번호 배열 (예: [1, 2]) */
  sourceRefs: number[];
}

/* ── Mock 데이터 ── */

const MOCK_L1_SUMMARY: SummaryBlock = {
  label: "L1 요약",
  content: "Q2 제품 로드맵에 대한 전략 회의. RAG 기반 검색 고도화를 최우선 과제로 선정하고, 디자인 시스템 v2 마이그레이션 일정을 확정했다. 보안통신 모듈은 별도 프로젝트로 분리하기로 결정.",
  sourceRefs: [1, 2],
};

const MOCK_L2_DECISIONS: SummaryBlock[] = [
  {
    label: "결정",
    content: "RAG 파이프라인 6-Layer 아키텍처 도입을 확정. 캐시 레이어를 최우선 구현한다.",
    sourceRefs: [1],
  },
  {
    label: "결정",
    content: "디자인 시스템 v2 마이그레이션은 4월 2주차 시작. Figma 토큰 자동 동기화 포함.",
    sourceRefs: [2, 3],
  },
  {
    label: "액션",
    content: "보안통신 모듈 요구사항 문서 작성 (담당: 박현우, 기한: 4/7).",
    sourceRefs: [3],
  },
];

const MOCK_SOURCES: SourceSnippet[] = [
  {
    id: 1,
    speaker: "김민수",
    timestamp: "03:42",
    text: "RAG 6-Layer를 도입하면 캐시 히트율이 크게 올라갈 겁니다. 먼저 캐시 레이어부터 구현하죠.",
  },
  {
    id: 2,
    speaker: "이지은",
    timestamp: "12:15",
    text: "디자인 시스템 v2는 4월 2주차에 시작할 수 있을 것 같아요. Figma 토큰 동기화도 이번에 같이 넣으면 좋겠습니다.",
  },
  {
    id: 3,
    speaker: "박현우",
    timestamp: "18:30",
    text: "보안통신 모듈은 별도 프로젝트로 분리하는 게 관리하기 편할 것 같습니다. 제가 요구사항 문서를 정리하겠습니다.",
  },
];

/* ── 컴포넌트 ── */

interface MeetingSummaryViewProps {
  onSwitchToTranscript: () => void;
}

export function MeetingSummaryView({ onSwitchToTranscript }: MeetingSummaryViewProps) {
  const [expandedSource, setExpandedSource] = useState<number | null>(null);

  function handleSourceClick(sourceId: number) {
    setExpandedSource((prev) => (prev === sourceId ? null : sourceId));
  }

  return (
    <div className="space-y-6">
      {/* L1 요약 블록 */}
      <div
        className="p-4 rounded-lg border"
        style={{
          background: "var(--surface)",
          borderColor: "var(--border-subtle)",
          borderRadius: "var(--radius-lg)",
        }}
      >
        <h3
          className="text-sm font-semibold mb-2"
          style={{ color: "var(--text-primary)", fontFamily: "var(--font-display)" }}
        >
          {MOCK_L1_SUMMARY.label}
        </h3>
        <p className="text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
          {MOCK_L1_SUMMARY.content}
          {MOCK_L1_SUMMARY.sourceRefs.map((ref) => (
            <SourceRef key={ref} id={ref} onClick={() => handleSourceClick(ref)} />
          ))}
        </p>
      </div>

      {/* L2 결정/액션 블록 */}
      <div
        className="p-4 rounded-lg border"
        style={{
          background: "var(--surface)",
          borderColor: "var(--border-subtle)",
          borderRadius: "var(--radius-lg)",
        }}
      >
        <h3
          className="text-sm font-semibold mb-3"
          style={{ color: "var(--text-primary)", fontFamily: "var(--font-display)" }}
        >
          결정사항 &middot; 액션
        </h3>
        <ul className="space-y-3">
          {MOCK_L2_DECISIONS.map((block, idx) => (
            <li key={idx} className="flex items-start gap-2">
              <span
                className="shrink-0 mt-0.5 text-xs"
                style={{ color: block.label === "액션" ? "var(--warning)" : "var(--accent)" }}
              >
                {block.label === "액션" ? "▸" : "•"}
              </span>
              <div className="text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                <span
                  className="text-[10px] font-medium mr-1 px-1 py-0.5 rounded"
                  style={{
                    background: block.label === "액션" ? "rgba(251,191,36,0.1)" : "var(--accent-subtle)",
                    color: block.label === "액션" ? "var(--warning)" : "var(--accent)",
                  }}
                >
                  {block.label}
                </span>
                {block.content}
                {block.sourceRefs.map((ref) => (
                  <SourceRef key={ref} id={ref} onClick={() => handleSourceClick(ref)} />
                ))}
              </div>
            </li>
          ))}
        </ul>
      </div>

      {/* 펼쳐진 출처 스니펫 */}
      {expandedSource !== null && (
        <SourceSnippetCard
          source={MOCK_SOURCES.find((s) => s.id === expandedSource) ?? null}
          onClose={() => setExpandedSource(null)}
        />
      )}

      {/* 트랜스크립트 전체 보기 링크 */}
      <div className="flex justify-end">
        <button
          onClick={onSwitchToTranscript}
          className="text-xs transition-colors"
          style={{ color: "var(--accent)", cursor: "pointer", minHeight: "44px" }}
        >
          트랜스크립트 전체 보기 →
        </button>
      </div>
    </div>
  );
}

/* ── 서브 컴포넌트 ── */

function SourceRef({ id, onClick }: { id: number; onClick: () => void }) {
  const style = SOURCE_STYLES[id] ?? SOURCE_STYLES[1];

  return (
    <button
      onClick={onClick}
      className="inline-flex items-center justify-center ml-1 px-1.5 py-0.5 rounded text-[10px] font-mono font-medium transition-opacity"
      style={{
        background: style.background,
        color: style.color,
        cursor: "pointer",
        verticalAlign: "super",
        lineHeight: 1,
      }}
    >
      [{id}]
    </button>
  );
}

function SourceSnippetCard({ source, onClose }: { source: SourceSnippet | null; onClose: () => void }) {
  if (!source) return null;

  const style = SOURCE_STYLES[source.id] ?? SOURCE_STYLES[1];

  return (
    <div
      className="p-4 rounded-lg border"
      style={{
        background: style.background,
        borderColor: style.color,
        borderRadius: "var(--radius-lg)",
        borderWidth: "1px",
      }}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span
            className="px-1.5 py-0.5 rounded text-[10px] font-mono font-medium"
            style={{ background: style.background, color: style.color }}
          >
            출처 [{source.id}]
          </span>
          <span className="text-xs font-medium" style={{ color: style.color }}>
            {source.speaker}
          </span>
          <span className="text-[10px]" style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
            {source.timestamp}
          </span>
        </div>
        <button
          onClick={onClose}
          className="text-xs"
          style={{ color: "var(--text-muted)", cursor: "pointer", minHeight: "44px" }}
        >
          닫기
        </button>
      </div>
      <p className="text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
        &ldquo;{source.text}&rdquo;
      </p>
    </div>
  );
}
