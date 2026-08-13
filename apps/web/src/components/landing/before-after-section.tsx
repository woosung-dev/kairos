"use client";

import { useReveal } from "@/hooks/use-reveal";

const WITHOUT_ITEMS = [
  '"회의록 어디에 있더라?"',
  '"왜 그렇게 결정했는지 기억이 안 나"',
  '"신입에게 맥락 전달이 몇 주 걸려"',
  '"지난번에도 같은 실수를 했는데..."',
];

const WITH_ITEMS = [
  "Cmd+K → 소스와 함께 즉시 답변",
  "모든 결정 맥락이 프로젝트에 자동 기록",
  "프로젝트 인사이트로 온보딩 80% 단축",
  "과거 교훈이 자동으로 표면화",
];

export function BeforeAfterSection() {
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
        이 문제들, 익숙하지 않으세요?
      </h2>

      {/* 2컬럼 그리드 */}
      <div className="mx-auto grid max-w-[740px] grid-cols-1 gap-3 md:grid-cols-2">
        {/* WITHOUT KAIROS */}
        <div
          className="overflow-hidden"
          style={{
            border: "1px solid var(--border)",
            borderRadius: 12,
            boxShadow: "var(--shadow-card)",
          }}
        >
          <div
            className="px-5 py-3.5"
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: 12,
              fontWeight: 600,
              letterSpacing: "0.04em",
              color: "var(--text-muted)",
              background: "var(--surface)",
              borderBottom: "1px solid var(--border-subtle)",
            }}
          >
            WITHOUT KAIROS
          </div>
          <div className="p-1.5">
            {WITHOUT_ITEMS.map((item) => (
              <div
                key={item}
                className="border-b px-4 py-3 last:border-b-0"
                style={{
                  fontSize: 14,
                  lineHeight: 1.6,
                  color: "var(--text-muted)",
                  borderColor: "var(--border-subtle)",
                }}
              >
                {item}
              </div>
            ))}
          </div>
        </div>

        {/* WITH KAIROS */}
        <div
          className="overflow-hidden"
          style={{
            border: "1px solid var(--border)",
            borderRadius: 12,
            boxShadow: "var(--shadow-card)",
          }}
        >
          <div
            className="px-5 py-3.5"
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: 12,
              fontWeight: 600,
              letterSpacing: "0.04em",
              color: "var(--accent)",
              background: "var(--accent-subtle)",
              borderBottom: "1px solid var(--border-subtle)",
            }}
          >
            WITH KAIROS
          </div>
          <div className="p-1.5">
            {WITH_ITEMS.map((item) => (
              <div
                key={item}
                className="border-b px-4 py-3 last:border-b-0"
                style={{
                  fontSize: 14,
                  lineHeight: 1.6,
                  color: "var(--text-primary)",
                  borderColor: "var(--border-subtle)",
                }}
              >
                {item}
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
