"use client";

import { useReveal } from "@/hooks/use-reveal";

interface StatItem {
  value: string;
  label: string;
}

const STATS: StatItem[] = [
  { value: "95%", label: "수동 정리 시간 절감" },
  { value: "12x", label: "지식 재활용률" },
  { value: "24h", label: "첫 인사이트까지" },
];

export function StatsSection() {
  const ref = useReveal<HTMLElement>();

  return (
    <section
      ref={ref}
      className="landing-reveal mx-auto max-w-[960px] px-6 py-20"
    >
      <div className="mx-auto grid max-w-[640px] grid-cols-1 gap-3 md:grid-cols-3">
        {STATS.map((stat) => (
          <div
            key={stat.value}
            className="rounded-xl p-6 text-center"
            style={{
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: 12,
              boxShadow: "var(--shadow-card)",
            }}
          >
            <div
              style={{
                fontFamily: "var(--font-display)",
                fontSize: 32,
                fontWeight: 900,
                color: "var(--accent)",
              }}
            >
              {stat.value}
            </div>
            <div
              className="mt-1"
              style={{
                fontSize: 13,
                color: "var(--text-secondary)",
              }}
            >
              {stat.label}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
