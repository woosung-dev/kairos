"use client";

import { useState, useMemo } from "react";

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

interface TranscriptEntry {
  id: string;
  speaker: string;
  timestamp: string;
  startSec: number;
  text: string;
  /** 이 발언이 해당하는 출처 번호 (없으면 빈 배열) */
  sourceMarkers: number[];
}

/* ── Mock 데이터 ── */

const MOCK_TRANSCRIPT: TranscriptEntry[] = [
  {
    id: "ts-001",
    speaker: "김민수",
    timestamp: "00:00",
    startSec: 0,
    text: "오늘 Q2 제품 로드맵 관련해서 세 가지 안건이 있습니다. 첫 번째는 RAG 파이프라인 아키텍처 결정입니다.",
    sourceMarkers: [],
  },
  {
    id: "ts-002",
    speaker: "이지은",
    timestamp: "01:15",
    startSec: 75,
    text: "RAG 관련해서 제가 리서치한 내용을 공유드리면, 6-Layer 아키텍처가 현재 시점에서 가장 적합해 보입니다.",
    sourceMarkers: [],
  },
  {
    id: "ts-003",
    speaker: "김민수",
    timestamp: "03:42",
    startSec: 222,
    text: "RAG 6-Layer를 도입하면 캐시 히트율이 크게 올라갈 겁니다. 먼저 캐시 레이어부터 구현하죠.",
    sourceMarkers: [1],
  },
  {
    id: "ts-004",
    speaker: "박현우",
    timestamp: "06:30",
    startSec: 390,
    text: "캐시 레이어 구현 일정은 어떻게 잡을까요? 2주 정도면 충분할까요?",
    sourceMarkers: [],
  },
  {
    id: "ts-005",
    speaker: "김민수",
    timestamp: "08:00",
    startSec: 480,
    text: "네, 2주면 충분합니다. 그다음 안건으로 넘어가서 디자인 시스템 v2 마이그레이션 일정을 논의하겠습니다.",
    sourceMarkers: [],
  },
  {
    id: "ts-006",
    speaker: "이지은",
    timestamp: "12:15",
    startSec: 735,
    text: "디자인 시스템 v2는 4월 2주차에 시작할 수 있을 것 같아요. Figma 토큰 동기화도 이번에 같이 넣으면 좋겠습니다.",
    sourceMarkers: [2],
  },
  {
    id: "ts-007",
    speaker: "최수진",
    timestamp: "15:45",
    startSec: 945,
    text: "Figma 토큰 동기화 관련해서 이미 PoC를 완료했습니다. 공유 드리겠습니다.",
    sourceMarkers: [],
  },
  {
    id: "ts-008",
    speaker: "박현우",
    timestamp: "18:30",
    startSec: 1110,
    text: "보안통신 모듈은 별도 프로젝트로 분리하는 게 관리하기 편할 것 같습니다. 제가 요구사항 문서를 정리하겠습니다.",
    sourceMarkers: [3],
  },
];

/* ── 컴포넌트 ── */

export function TranscriptView() {
  const [searchQuery, setSearchQuery] = useState("");

  const filteredTranscript = useMemo(() => {
    if (!searchQuery.trim()) return MOCK_TRANSCRIPT;
    const q = searchQuery.toLowerCase();
    return MOCK_TRANSCRIPT.filter(
      (entry) =>
        entry.text.toLowerCase().includes(q) ||
        entry.speaker.toLowerCase().includes(q)
    );
  }, [searchQuery]);

  return (
    <div className="space-y-4">
      {/* 검색 입력 */}
      <div className="relative">
        <input
          type="text"
          placeholder="트랜스크립트 검색..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
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
        {filteredTranscript.map((entry) => (
          <TranscriptEntryRow key={entry.id} entry={entry} searchQuery={searchQuery} />
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

/* ── 서브 컴포넌트 ── */

function TranscriptEntryRow({ entry, searchQuery }: { entry: TranscriptEntry; searchQuery: string }) {
  const hasSourceMarkers = entry.sourceMarkers.length > 0;

  return (
    <div
      className="flex gap-3 px-3 py-2 rounded-lg transition-colors"
      style={{
        background: hasSourceMarkers ? "var(--surface)" : "transparent",
        borderRadius: "var(--radius-lg)",
      }}
    >
      {/* 타임스탬프 */}
      <span
        className="shrink-0 text-xs pt-0.5"
        style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)", width: "44px" }}
      >
        {entry.timestamp}
      </span>

      {/* 화자 + 텍스트 */}
      <div className="flex-1 min-w-0">
        <span className="text-xs font-medium mr-2" style={{ color: "var(--accent)" }}>
          {entry.speaker}
        </span>
        <span className="text-sm" style={{ color: "var(--text-secondary)" }}>
          {highlightText(entry.text, searchQuery)}
        </span>

        {/* 출처 마커 */}
        {hasSourceMarkers && (
          <span className="inline-flex items-center gap-1 ml-2">
            {entry.sourceMarkers.map((markerId) => {
              const style = SOURCE_STYLES[markerId] ?? SOURCE_STYLES[1];
              return (
                <span
                  key={markerId}
                  className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono font-medium"
                  style={{
                    background: style.background,
                    color: style.color,
                  }}
                >
                  [{markerId}]
                </span>
              );
            })}
          </span>
        )}
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
