"use client";

import { useReveal } from "@/hooks/use-reveal";

interface TimelineStep {
  marker: string;
  markerClass: "mk1" | "mk2" | "mk3";
  time: string;
  title: string;
  description: string;
  tags: string[];
}

const TIMELINE_STEPS: TimelineStep[] = [
  {
    marker: "W1",
    markerClass: "mk1",
    time: "WEEK 1",
    title: "흩어진 지식이 한 곳에 모인다",
    description:
      "5분 설정, AI가 전사·요약·액션 아이템을 자동 추출하고 프로젝트에 연결.",
    tags: ["자동 전사", "화자 분리", "AI 요약"],
  },
  {
    marker: "M1",
    markerClass: "mk2",
    time: "MONTH 1",
    title: "지식이 연결되고 인사이트가 나타난다",
    description:
      "프로젝트 간 교차 인사이트 등장. 신입 온보딩 시간이 절반으로.",
    tags: ["프로젝트 인사이트", "온보딩 단축"],
  },
  {
    marker: "Q1",
    markerClass: "mk3",
    time: "QUARTER 1",
    title: "조직이 같은 실수를 반복하지 않는다",
    description:
      "끝난 프로젝트의 교훈이 프로액티브 인사이트로 표면화. 팀이 진화합니다.",
    tags: ["조직 인사이트 (L4)", "교훈 재활용"],
  },
];

/** 마커 스타일 매핑 */
const MARKER_STYLES: Record<
  TimelineStep["markerClass"],
  { background: string; color: string; border: string }
> = {
  mk1: {
    background: "var(--cat-project-bg)",
    color: "var(--cat-project)",
    border: "1px solid var(--accent-bd)",
  },
  mk2: {
    background: "var(--cat-resource-bg)",
    color: "var(--cat-resource)",
    border: "1px solid rgba(124,58,237,0.15)",
  },
  mk3: {
    background: "var(--cat-area-bg)",
    color: "var(--cat-area)",
    border: "1px solid rgba(217,119,6,0.15)",
  },
};

export function EvolutionTimeline() {
  const ref = useReveal<HTMLElement>();

  return (
    <section
      ref={ref}
      className="landing-reveal mx-auto max-w-[960px] px-6 py-20"
    >
      {/* 제목 */}
      <h2
        className="mb-12 text-center"
        style={{
          fontFamily: "var(--font-display)",
          fontSize: 28,
          fontWeight: 700,
          letterSpacing: "-0.02em",
          color: "var(--text-primary)",
        }}
      >
        팀이 진화하는 세 단계
      </h2>

      {/* 타임라인 */}
      <div
        className="relative mx-auto max-w-[680px] pl-7"
        style={{ paddingLeft: 28 }}
      >
        {/* 세로 선 (pseudo 요소 대체 — div로 구현) */}
        <div
          className="absolute top-6 bottom-6"
          style={{
            left: 7,
            width: 1,
            background:
              "linear-gradient(to bottom, var(--cat-project), var(--cat-resource), var(--border))",
          }}
        />

        {TIMELINE_STEPS.map((step) => {
          const markerStyle = MARKER_STYLES[step.markerClass];
          return (
            <div
              key={step.marker}
              className="flex gap-5 py-6"
              style={{ marginLeft: 0 }}
            >
              {/* 원형 마커 */}
              <div
                className="relative z-10 flex shrink-0 items-center justify-center rounded-full"
                style={{
                  width: 44,
                  height: 44,
                  marginLeft: -22,
                  fontFamily: "var(--font-mono)",
                  fontSize: 12,
                  fontWeight: 600,
                  ...markerStyle,
                }}
              >
                {step.marker}
              </div>

              {/* 콘텐츠 */}
              <div>
                <div
                  className="mb-1"
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: 11,
                    color: "var(--text-muted)",
                    letterSpacing: "0.04em",
                  }}
                >
                  {step.time}
                </div>
                <h3
                  className="mb-1"
                  style={{
                    fontFamily: "var(--font-display)",
                    fontSize: 16,
                    fontWeight: 700,
                    color: "var(--text-primary)",
                  }}
                >
                  {step.title}
                </h3>
                <p
                  style={{
                    fontSize: 14,
                    color: "var(--text-secondary)",
                    lineHeight: 1.6,
                  }}
                >
                  {step.description}
                </p>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {step.tags.map((tag) => (
                    <span
                      key={tag}
                      className="rounded px-2 py-0.5"
                      style={{
                        fontSize: 11,
                        background: "var(--surface-hover)",
                        border: "1px solid var(--border)",
                        color: "var(--text-secondary)",
                        borderRadius: 4,
                      }}
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
