"use client";

import { Search } from "lucide-react";
import { useReveal } from "@/hooks/use-reveal";

interface SearchResult {
  type: string;
  isHighlighted: boolean;
  title: string;
  body: string;
  source: string;
}

const SEARCH_RESULTS: SearchResult[] = [
  {
    type: "인사이트",
    isHighlighted: true,
    title: "Q1 런칭 지연 원인: QA 시작 시점 문제",
    body: "개발 완료 2주 후에야 QA 시작. 긴급 버그 수정으로 일정 초과.",
    source: "Q1 프로젝트 아카이브 · L4 조직 인사이트",
  },
  {
    type: "교훈",
    isHighlighted: false,
    title: "현재 프로젝트에서 유사 패턴 감지",
    body: "QA 계획 미수립 상태. 조기 QA 시작을 권장합니다.",
    source: "프로액티브 인사이트 · 유사도 89%",
  },
  {
    type: "회의",
    isHighlighted: false,
    title: 'Q1 회고: "QA를 스프린트 초반부터"',
    body: "팀 합의: 다음 프로젝트부터 QA 병행 진행.",
    source: "1/28 회고 회의 · 결정사항",
  },
];

export function SearchDemoSection() {
  const ref = useReveal<HTMLElement>();

  return (
    <section
      ref={ref}
      className="landing-reveal mx-auto max-w-[620px] px-6 pt-5 pb-20"
    >
      {/* 라벨 */}
      <p
        className="mb-4 text-center"
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: 11,
          color: "var(--text-muted)",
          letterSpacing: "0.04em",
        }}
      >
        CMD+K &mdash; 정리된 지식이 이렇게 활용됩니다
      </p>

      {/* 검색 박스 */}
      <div
        className="overflow-hidden"
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: 12,
          boxShadow: "var(--shadow-card-hover)",
        }}
      >
        {/* 입력줄 */}
        <div
          className="flex items-center gap-3 px-5 py-4"
          style={{ borderBottom: "1px solid var(--border-subtle)" }}
        >
          <Search
            size={16}
            className="shrink-0"
            style={{ color: "var(--text-muted)" }}
          />
          <span
            className="flex-1"
            style={{ fontSize: 15, color: "var(--text-primary)" }}
          >
            지난 프로젝트에서 런칭이 왜 늦어졌지?
          </span>
          <kbd
            className="shrink-0 rounded"
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: 10,
              color: "var(--text-muted)",
              background: "var(--surface-hover)",
              padding: "3px 10px",
              border: "1px solid var(--border-subtle)",
              borderRadius: 4,
            }}
          >
            &#8984;K
          </kbd>
        </div>

        {/* 결과 목록 */}
        <div className="p-1.5">
          {SEARCH_RESULTS.map((result) => (
            <div
              key={result.title}
              className="flex gap-3 rounded-lg p-3"
              style={{
                background: result.isHighlighted
                  ? "var(--accent-subtle)"
                  : "transparent",
                borderRadius: "var(--radius-lg)",
              }}
            >
              {/* 타입 배지 */}
              <span
                className="mt-0.5 shrink-0 whitespace-nowrap rounded"
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: 10,
                  fontWeight: 500,
                  padding: "3px 7px",
                  borderRadius: 3,
                  border: result.isHighlighted
                    ? "1px solid var(--accent-bd)"
                    : "1px solid var(--border-subtle)",
                  color: result.isHighlighted
                    ? "var(--accent)"
                    : "var(--text-muted)",
                }}
              >
                {result.type}
              </span>

              {/* 본문 */}
              <div>
                <h4
                  className="mb-0.5"
                  style={{
                    fontSize: 14,
                    fontWeight: 600,
                    color: "var(--text-primary)",
                  }}
                >
                  {result.title}
                </h4>
                <p
                  style={{
                    fontSize: 12,
                    color: "var(--text-muted)",
                    lineHeight: 1.55,
                  }}
                >
                  {result.body}
                </p>
                <div
                  className="mt-1"
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: 11,
                    color: "var(--accent)",
                  }}
                >
                  {result.source}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
