"use client";

import { useState } from "react";
import { SmartInboxItemCard } from "./inbox-item-card";
import type { UUID } from "@/types";

/* ── Mock 타입 ── */

interface SmartInboxItem {
  id: UUID;
  title: string;
  sourceType: "meeting" | "note" | "attachment";
  aiSuggestedProject: string;
  aiConfidence: number;
  aiSuggestedTags: string[];
  summary: string | null;
  isAutoProcessed: boolean;
}

/* ── Mock 데이터 ── */

const MOCK_NEEDS_REVIEW: SmartInboxItem[] = [
  {
    id: "inbox-001",
    title: "경쟁사 제품 분석 미팅",
    sourceType: "meeting",
    aiSuggestedProject: "Q2 제품 로드맵",
    aiConfidence: 0.72,
    aiSuggestedTags: ["경쟁분석", "전략"],
    summary: "Notion AI, Mem, Reflect 기능 비교 분석. 차별화 전략 논의 필요.",
    isAutoProcessed: false,
  },
  {
    id: "inbox-002",
    title: "인프라 비용 절감 메모",
    sourceType: "note",
    aiSuggestedProject: "DevOps 개선",
    aiConfidence: 0.65,
    aiSuggestedTags: ["인프라", "비용"],
    summary: "Cloud Run 스케일링 정책 조정으로 월 $200 절감 가능성 파악.",
    isAutoProcessed: false,
  },
];

const MOCK_AUTO_PROCESSED: SmartInboxItem[] = [
  {
    id: "inbox-003",
    title: "주간 스프린트 리뷰",
    sourceType: "meeting",
    aiSuggestedProject: "Q2 제품 로드맵",
    aiConfidence: 0.98,
    aiSuggestedTags: ["스프린트", "리뷰"],
    summary: "Sprint 4 배포 완료 확인. Sprint 5 백로그 우선순위 결정.",
    isAutoProcessed: true,
  },
  {
    id: "inbox-004",
    title: "디자인 시스템 문서",
    sourceType: "attachment",
    aiSuggestedProject: "디자인 시스템",
    aiConfidence: 0.95,
    aiSuggestedTags: ["디자인", "문서"],
    summary: "Figma 토큰 명세서 PDF. 컴포넌트 라이브러리 v2 기준.",
    isAutoProcessed: true,
  },
  {
    id: "inbox-005",
    title: "사용자 인터뷰 녹음",
    sourceType: "meeting",
    aiSuggestedProject: "사용자 리서치",
    aiConfidence: 0.93,
    aiSuggestedTags: ["UX", "인터뷰"],
    summary: "베타 사용자 3명 심층 인터뷰. 검색 기능 만족도 높음.",
    isAutoProcessed: true,
  },
  {
    id: "inbox-006",
    title: "API 성능 테스트 결과",
    sourceType: "attachment",
    aiSuggestedProject: "DevOps 개선",
    aiConfidence: 0.91,
    aiSuggestedTags: ["API", "성능"],
    summary: "RAG 엔드포인트 p95 응답시간 320ms. 목표 대비 양호.",
    isAutoProcessed: true,
  },
  {
    id: "inbox-007",
    title: "팀 회고 미팅",
    sourceType: "meeting",
    aiSuggestedProject: "Q2 제품 로드맵",
    aiConfidence: 0.90,
    aiSuggestedTags: ["회고", "팀"],
    summary: "Sprint 3-4 회고. 코드 리뷰 프로세스 개선 합의.",
    isAutoProcessed: true,
  },
];

/* ── 컴포넌트 ── */

export function SmartInbox() {
  const [isAutoExpanded, setIsAutoExpanded] = useState(false);

  const needsReviewCount = MOCK_NEEDS_REVIEW.length;
  const autoProcessedCount = MOCK_AUTO_PROCESSED.length;

  return (
    <div className="p-6">
      {/* 헤더 */}
      <div className="mb-6">
        <h1
          className="text-2xl font-bold mb-1"
          style={{ fontFamily: "var(--font-display)", color: "var(--text-primary)" }}
        >
          Inbox
        </h1>
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          AI가 분류한 항목을 확인하고 프로젝트에 연결하세요
        </p>
      </div>

      {/* 확인 필요 그룹 */}
      {needsReviewCount > 0 && (
        <section className="mb-8">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-base">⚠️</span>
            <h2
              className="text-sm font-semibold"
              style={{ color: "var(--warning)", fontFamily: "var(--font-display)" }}
            >
              확인 필요
            </h2>
            <span
              className="px-1.5 py-0.5 rounded-full text-[10px] font-medium"
              style={{
                background: "rgba(251,191,36,0.1)",
                color: "var(--warning)",
              }}
            >
              {needsReviewCount}건
            </span>
          </div>
          <div className="grid gap-3">
            {MOCK_NEEDS_REVIEW.map((item) => (
              <SmartInboxItemCard key={item.id} item={item} />
            ))}
          </div>
        </section>
      )}

      {/* AI 자동 처리 그룹 */}
      {autoProcessedCount > 0 && (
        <section>
          <button
            onClick={() => setIsAutoExpanded(!isAutoExpanded)}
            className="flex items-center gap-2 mb-3 w-full text-left"
            style={{ cursor: "pointer", minHeight: "44px" }}
          >
            <span className="text-base">✅</span>
            <h2
              className="text-sm font-semibold"
              style={{ color: "var(--success)", fontFamily: "var(--font-display)" }}
            >
              AI가 자동 처리한 항목
            </h2>
            <span
              className="px-1.5 py-0.5 rounded-full text-[10px] font-medium"
              style={{
                background: "rgba(52,211,153,0.1)",
                color: "var(--success)",
              }}
            >
              {autoProcessedCount}건
            </span>
            <span
              className="ml-auto text-xs transition-transform"
              style={{
                color: "var(--text-muted)",
                transform: isAutoExpanded ? "rotate(180deg)" : "rotate(0deg)",
              }}
            >
              ▼
            </span>
          </button>

          {isAutoExpanded && (
            <div className="grid gap-3">
              {MOCK_AUTO_PROCESSED.map((item) => (
                <SmartInboxItemCard key={item.id} item={item} />
              ))}
            </div>
          )}
        </section>
      )}

      {/* 모두 비어있을 때 */}
      {needsReviewCount === 0 && autoProcessedCount === 0 && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <span className="text-4xl mb-4">📥</span>
          <h3
            className="text-lg font-semibold mb-2"
            style={{ color: "var(--text-primary)", fontFamily: "var(--font-display)" }}
          >
            처리할 항목이 없습니다
          </h3>
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            회의를 녹음하거나 노트를 추가하면 AI가 자동으로 분류합니다
          </p>
        </div>
      )}
    </div>
  );
}
