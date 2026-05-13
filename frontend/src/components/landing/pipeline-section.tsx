"use client";

import { useReveal } from "@/hooks/use-reveal";

interface PipelineCard {
  letter: string;
  title: string;
  description: string;
  detail: string;
  isCore: boolean;
}

const PIPELINE_CARDS: PipelineCard[] = [
  {
    letter: "C",
    title: "Capture",
    description: "마찰 없는 입력. 녹음, 노트, 문서를 드래그 앤 드롭으로.",
    detail: "Whisper API · 화자 분리",
    isCore: false,
  },
  {
    letter: "O",
    title: "Organize",
    description: "AI가 프로젝트에 자동 연결하고 태그를 부여합니다.",
    detail: "자동 매핑 · Inbox",
    isCore: false,
  },
  {
    letter: "D",
    title: "Distill",
    description: "4단계 자동 증류. 개별 요약에서 조직 인사이트까지.",
    detail: "L1→L2→L3→L4",
    isCore: true,
  },
  {
    letter: "E",
    title: "Express",
    description: "축적된 지식을 AI Q&A로 즉시 꺼냅니다.",
    detail: "소스 명시 · 신뢰도",
    isCore: false,
  },
];

interface DistillLevel {
  label: string;
  name: string;
  colorVar: string;
}

const DISTILL_LEVELS: DistillLevel[] = [
  { label: "L1", name: "콘텐츠 요약", colorVar: "var(--cat-project)" },
  { label: "L2", name: "결정 + 액션", colorVar: "var(--cat-area)" },
  { label: "L3", name: "프로젝트 인사이트", colorVar: "var(--cat-resource)" },
  { label: "L4", name: "조직 인사이트", colorVar: "var(--cat-archive)" },
];

export function PipelineSection() {
  const sectionRef = useReveal<HTMLElement>();
  const distillRef = useReveal<HTMLElement>();

  return (
    <>
      <section
        ref={sectionRef}
        id="pipe"
        className="landing-reveal mx-auto max-w-[960px] px-6 py-20"
      >
        {/* 제목 */}
        <h2
          className="mb-2 text-center"
          style={{
            fontFamily: "var(--font-display)",
            fontSize: 28,
            fontWeight: 700,
            letterSpacing: "-0.02em",
            color: "var(--text-primary)",
          }}
        >
          CODE 파이프라인
        </h2>
        <p
          className="mb-12 text-center"
          style={{
            fontSize: 15,
            color: "var(--text-secondary)",
          }}
        >
          입력은 편하게, 정리는 AI가, 재활용은 자동으로
        </p>

        {/* 파이프라인 카드 row */}
        <div className="flex flex-col items-stretch gap-3 md:flex-row">
          {PIPELINE_CARDS.map((card, index) => (
            <div key={card.letter} className="flex flex-col items-stretch gap-3 md:flex-row md:flex-1">
              {/* 카드 */}
              <div
                className="relative flex-1 cursor-default rounded-xl p-5 transition-all duration-200 md:p-7 hover:-translate-y-0.5"
                style={{
                  background: card.isCore
                    ? "var(--accent-subtle)"
                    : "var(--surface)",
                  border: card.isCore
                    ? "1px solid var(--accent)"
                    : "1px solid var(--border)",
                  borderRadius: 12,
                  boxShadow: card.isCore
                    ? "0 2px 12px rgba(15,168,137,0.08)"
                    : "var(--shadow-card)",
                }}
              >
                {/* 대형 배경 letter */}
                <span
                  className="pointer-events-none absolute top-4 right-4 leading-none select-none"
                  style={{
                    fontFamily: "var(--font-display)",
                    fontSize: 36,
                    fontWeight: 900,
                    color: "var(--accent)",
                    opacity: card.isCore ? 0.3 : 0.12,
                  }}
                >
                  {card.letter}
                </span>

                <h3
                  className="mb-1.5"
                  style={{
                    fontSize: 16,
                    fontWeight: 700,
                    fontFamily: "var(--font-display)",
                    color: "var(--text-primary)",
                  }}
                >
                  {card.title}
                </h3>
                <p
                  style={{
                    fontSize: 13,
                    color: "var(--text-secondary)",
                    lineHeight: 1.65,
                  }}
                >
                  {card.description}
                </p>
                <div
                  className="mt-3 border-t pt-3"
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: 11,
                    color: "var(--text-muted)",
                    borderColor: "var(--border-subtle)",
                  }}
                >
                  {card.detail}
                </div>
              </div>

              {/* 화살표 (마지막 카드 뒤에는 없음) */}
              {index < PIPELINE_CARDS.length - 1 && (
                <span
                  className="flex shrink-0 items-center justify-center text-lg md:rotate-0"
                  style={{
                    color: "var(--text-muted)",
                    fontSize: 18,
                    padding: "4px 0",
                  }}
                >
                  <span className="rotate-90 md:rotate-0">&rarr;</span>
                </span>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Distill 하이라이트 */}
      <section
        ref={distillRef}
        className="landing-reveal mx-auto -mt-8 max-w-[700px] px-6"
      >
        <div
          className="flex flex-col items-center justify-center gap-4 rounded-xl p-6 md:flex-row md:flex-wrap"
          style={{
            border: "1px solid var(--accent-bd)",
            borderRadius: 12,
            background: "var(--accent-subtle)",
          }}
        >
          <span
            className="shrink-0 whitespace-nowrap"
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: 11,
              color: "var(--accent)",
              letterSpacing: "0.04em",
            }}
          >
            DISTILL 4-LEVEL
          </span>

          <div className="flex flex-wrap justify-center gap-2">
            {DISTILL_LEVELS.map((level) => (
              <span
                key={level.label}
                className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5"
                style={{
                  background: "var(--surface)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "var(--radius-lg)",
                  fontSize: 12,
                }}
              >
                <span
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontWeight: 600,
                    color: level.colorVar,
                  }}
                >
                  {level.label}
                </span>
                <span
                  style={{
                    fontWeight: 500,
                    color: "var(--text-secondary)",
                  }}
                >
                  {level.name}
                </span>
              </span>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}
