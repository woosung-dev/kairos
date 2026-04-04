"use client";

import { useEffect, useRef, useMemo, useState, type ReactNode } from "react";
import { X, Copy, ExternalLink, Check } from "lucide-react";
import { getCitationColor } from "@/features/rag/components/citation-badge";
import type { SourceDocument, HighlightChunk } from "../types";

interface SourceViewerProps {
  source: SourceDocument;
  highlightChunks?: HighlightChunk[];
  onClose: () => void;
}

/** 하이라이트 색상: citation 번호별 border-left + 배경 */
function getHighlightStyle(citationNumber: number): {
  background: string;
  borderLeft: string;
} {
  const palette = getCitationColor(citationNumber);
  return {
    background: palette.bg,
    borderLeft: `3px solid ${palette.color}`,
  };
}

/** 소스 타입별 아이콘 */
const SOURCE_TYPE_ICON: Record<string, string> = {
  meeting: "\uD83C\uDF99\uFE0F",
  note: "\uD83D\uDCDD",
  file: "\uD83D\uDCC4",
};

/** 콘텐츠에 하이라이트를 적용하여 ReactNode 배열로 변환 */
function renderHighlightedContent(
  content: string,
  chunks: HighlightChunk[],
): ReactNode[] {
  if (chunks.length === 0) {
    return [content];
  }

  // offset 순으로 정렬 (겹치지 않는다고 가정)
  const sorted = [...chunks].sort((a, b) => a.startOffset - b.startOffset);
  const parts: ReactNode[] = [];
  let cursor = 0;

  sorted.forEach((chunk, idx) => {
    const start = Math.max(chunk.startOffset, cursor);
    const end = Math.min(chunk.endOffset, content.length);

    // 하이라이트 앞 일반 텍스트
    if (start > cursor) {
      parts.push(
        <span key={`text-${idx}`}>{content.slice(cursor, start)}</span>,
      );
    }

    const style = getHighlightStyle(chunk.citationNumber);
    parts.push(
      <mark
        key={`hl-${idx}`}
        data-citation={chunk.citationNumber}
        className="px-2 py-0.5 rounded-sm inline"
        style={{
          background: style.background,
          borderLeft: style.borderLeft,
          color: "var(--text-primary)",
          borderRadius: "var(--radius-sm)",
        }}
      >
        {content.slice(start, end)}
      </mark>,
    );

    cursor = end;
  });

  // 남은 텍스트
  if (cursor < content.length) {
    parts.push(
      <span key="text-tail">{content.slice(cursor)}</span>,
    );
  }

  return parts;
}

/** mock 소스 데이터 */
export const MOCK_SOURCES: SourceDocument[] = [
  {
    id: "src-1",
    title: "Sprint 3 회고 회의",
    type: "meeting",
    content:
      "이번 Sprint 3에서는 RAG 파이프라인 통합과 노트 기능을 완료했습니다. 주요 성과로는 6-Layer RAG 아키텍처 구현, 하이브리드 검색(키워드+벡터), 시맨틱 캐시 적용이 있습니다. 다음 Sprint에서는 배포 인프라 구축에 집중할 예정입니다. Cloud Run과 Vercel을 활용한 프로덕션 환경 구성이 핵심 과제입니다.",
    projectId: "proj-1",
    createdAt: "2026-03-28T10:00:00Z",
  },
  {
    id: "src-2",
    title: "RAG 파이프라인 설계 노트",
    type: "note",
    content:
      "RAG 6-Layer 아키텍처: Cache Layer -> Query Processing -> Hybrid Search -> Re-ranking -> Generation -> Cache Store. 임베딩 모델은 OpenAI text-embedding-3-small (1536d)을 사용합니다. 쿼리 처리 단계에서 의도 분석과 키워드 추출을 수행하고, 하이브리드 검색으로 BM25와 벡터 검색을 결합합니다. Re-ranking은 cross-encoder를 통해 정밀도를 높입니다.",
    projectId: "proj-1",
    createdAt: "2026-03-25T14:30:00Z",
  },
  {
    id: "src-3",
    title: "배포 가이드.md",
    type: "file",
    content:
      "Kairos 배포 가이드\n\n1. Backend: GCP Cloud Run\n- Docker 이미지 빌드 후 Artifact Registry 푸시\n- Cloud Run 서비스 배포 (min-instances: 0, max: 10)\n- 환경변수: DATABASE_URL, CLERK_SECRET_KEY 등\n\n2. Frontend: Vercel\n- GitHub 연동 자동 배포\n- 환경변수: NEXT_PUBLIC_API_URL, NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY\n\n3. Database: Neon PostgreSQL\n- 프로덕션 브랜치 사용\n- Connection pooling 활성화",
    projectId: "proj-2",
    createdAt: "2026-04-01T09:00:00Z",
  },
];

export const MOCK_HIGHLIGHTS: HighlightChunk[] = [
  {
    citationNumber: 1,
    startOffset: 0,
    endOffset: 64,
    text: "이번 Sprint 3에서는 RAG 파이프라인 통합과 노트 기능을 완료했습니다.",
  },
  {
    citationNumber: 2,
    startOffset: 0,
    endOffset: 45,
    text: "RAG 6-Layer 아키텍처: Cache Layer -> Query Processing",
  },
];

export function SourceViewer({
  source,
  highlightChunks = [],
  onClose,
}: SourceViewerProps) {
  const contentRef = useRef<HTMLDivElement>(null);
  const [isCopied, setIsCopied] = useState(false);

  // 첫 번째 하이라이트 위치로 자동 스크롤
  useEffect(() => {
    if (highlightChunks.length === 0) return;
    const timer = setTimeout(() => {
      const firstMark = contentRef.current?.querySelector("mark");
      if (firstMark) {
        firstMark.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    }, 100);
    return () => clearTimeout(timer);
  }, [highlightChunks]);

  const renderedContent = useMemo(
    () => renderHighlightedContent(source.content, highlightChunks),
    [source.content, highlightChunks],
  );

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(source.content);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2000);
    } catch {
      // 클립보드 접근 실패 시 무시
    }
  };

  const icon = SOURCE_TYPE_ICON[source.type] ?? "\uD83D\uDCC4";

  return (
    <div
      className="flex flex-col h-full"
      style={{ background: "var(--background)" }}
    >
      {/* 헤더 */}
      <div
        className="flex items-center justify-between px-4 py-3 border-b shrink-0"
        style={{ borderColor: "var(--border-subtle)" }}
      >
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-base">{icon}</span>
          <h2
            className="text-sm font-semibold truncate"
            style={{
              color: "var(--text-primary)",
              fontFamily: "var(--font-display)",
            }}
          >
            {source.title}
          </h2>
          {highlightChunks.length > 0 && (
            <span
              className="shrink-0 px-1.5 py-0.5 rounded text-[10px]"
              style={{
                background: "var(--accent-subtle)",
                color: "var(--accent)",
                borderRadius: "var(--radius-sm)",
              }}
            >
              {highlightChunks.length}개 매치
            </span>
          )}
        </div>

        <div className="flex items-center gap-1 shrink-0">
          <button
            type="button"
            onClick={handleCopy}
            className="p-1.5 rounded transition-colors cursor-pointer"
            style={{ color: isCopied ? "var(--accent)" : "var(--text-muted)" }}
            onMouseOver={(e) => {
              e.currentTarget.style.background = "var(--surface-hover)";
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.background = "transparent";
            }}
            aria-label="복사"
          >
            {isCopied ? <Check size={14} /> : <Copy size={14} />}
          </button>

          <button
            type="button"
            className="p-1.5 rounded transition-colors cursor-pointer"
            style={{ color: "var(--text-muted)" }}
            onMouseOver={(e) => {
              e.currentTarget.style.background = "var(--surface-hover)";
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.background = "transparent";
            }}
            aria-label="내보내기"
          >
            <ExternalLink size={14} />
          </button>

          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded transition-colors cursor-pointer"
            style={{ color: "var(--text-muted)" }}
            onMouseOver={(e) => {
              e.currentTarget.style.background = "var(--surface-hover)";
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.background = "transparent";
            }}
            aria-label="닫기"
          >
            <X size={14} />
          </button>
        </div>
      </div>

      {/* 메타 정보 */}
      <div
        className="flex items-center gap-3 px-4 py-2 border-b text-[11px]"
        style={{
          borderColor: "var(--border-subtle)",
          color: "var(--text-muted)",
        }}
      >
        <span>{source.type === "meeting" ? "회의" : source.type === "note" ? "노트" : "파일"}</span>
        <span>|</span>
        <span>
          {new Date(source.createdAt).toLocaleDateString("ko-KR", {
            year: "numeric",
            month: "short",
            day: "numeric",
          })}
        </span>
      </div>

      {/* 본문 */}
      <div
        ref={contentRef}
        className="flex-1 overflow-y-auto px-4 py-4"
      >
        <div
          className="text-sm leading-relaxed whitespace-pre-wrap"
          style={{ color: "var(--text-primary)" }}
        >
          {renderedContent}
        </div>
      </div>
    </div>
  );
}
