"use client";

import { useEffect, useRef, useMemo, useState, type ReactNode } from "react";
import { X, Copy, ExternalLink, Check } from "lucide-react";
import { getCitationColor } from "@/features/rag/components/citation-badge";
import { useMeetingDetail } from "@/features/meetings/hooks";
import { useNote } from "@/features/notes/hooks";
import { useWorkspaceStore } from "@/features/workspaces/store";
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

/**
 * source.type이 meeting/note일 때 풀콘텐츠를 조회한다.
 * 로딩 중이거나 API 실패 시 RAG 응답의 스니펫(source.content)으로 폴백.
 */
function useFullSourceContent(source: SourceDocument): {
  content: string;
  isLoading: boolean;
} {
  const wid = useWorkspaceStore((s) => s.activeWorkspaceId) ?? undefined;

  const isMeeting = source.type === "meeting";
  const isNote = source.type === "note";

  // CAND-E: full-detail fetch 는 source 엔티티 PK(sourceId)로 — source.id 는 chunk PK 라
  // /meetings/{chunkId} 가 항상 404 → console retry storm. sourceId 미지정 시 id 폴백(하위호환).
  const entityId = source.sourceId ?? source.id;

  const meetingDetail = useMeetingDetail(
    isMeeting ? wid : undefined,
    entityId,
  );
  const noteDetail = useNote(isNote ? wid : undefined, entityId);

  if (isMeeting) {
    const transcript = meetingDetail.data?.transcript;
    if (transcript && transcript.length > 0) {
      return {
        content: transcript
          .map((seg) => `[${seg.speaker}] ${seg.text}`)
          .join("\n\n"),
        isLoading: false,
      };
    }
    const summary = meetingDetail.data?.summary?.summary;
    if (summary) return { content: summary, isLoading: false };
    return { content: source.content, isLoading: meetingDetail.isLoading };
  }

  if (isNote) {
    const plain = noteDetail.data?.plainText;
    if (plain) return { content: plain, isLoading: false };
    return { content: source.content, isLoading: noteDetail.isLoading };
  }

  // file 타입은 전용 API가 없어 RAG 스니펫 그대로
  return { content: source.content, isLoading: false };
}

export function SourceViewer({
  source,
  highlightChunks = [],
  onClose,
}: SourceViewerProps) {
  const contentRef = useRef<HTMLDivElement>(null);
  const [isCopied, setIsCopied] = useState(false);

  const { content, isLoading } = useFullSourceContent(source);

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
  }, [highlightChunks, content]);

  const renderedContent = useMemo(
    () => renderHighlightedContent(content, highlightChunks),
    [content, highlightChunks],
  );

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2000);
    } catch {
      // 클립보드 접근 실패 시 무시
    }
  };

  const icon = SOURCE_TYPE_ICON[source.type] ?? "\uD83D\uDCC4";

  return (
    <div
      data-testid="rag-source-viewer"
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
              className="shrink-0 px-1.5 py-0.5 rounded text-micro"
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
        className="flex items-center gap-3 px-4 py-2 border-b text-caption"
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
        {isLoading && (
          <div
            className="mb-3 text-caption"
            style={{ color: "var(--text-muted)" }}
          >
            전체 내용 불러오는 중...
          </div>
        )}
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
