"use client";

import Link from "next/link";
import { useReveal } from "@/hooks/use-reveal";

export function HeroSection() {
  const ref = useReveal<HTMLElement>();

  return (
    <section
      ref={ref}
      className="landing-reveal mx-auto max-w-[800px] px-6 pt-[152px] pb-12 text-center md:px-6"
      style={{ paddingTop: 152 }}
    >
      {/* 배지 — CODE 파이프라인 */}
      <div
        className="mb-7 inline-block rounded-full px-3.5 py-1.5"
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: 12,
          color: "var(--accent)",
          background: "var(--accent-subtle)",
          border: "1px solid var(--accent-bd)",
        }}
      >
        Capture &rarr; Organize &rarr; Distill &rarr; Express
      </div>

      {/* 헤드라인 */}
      <h1
        className="mb-5"
        style={{
          fontFamily: "var(--font-display)",
          fontSize: "clamp(32px, 5.5vw, 52px)",
          fontWeight: 900,
          lineHeight: 1.1,
          letterSpacing: "-0.035em",
          color: "var(--text-primary)",
        }}
      >
        AI가 정리합니다.
        <br />
        <span style={{ color: "var(--accent)" }}>당신은 결정만 하세요.</span>
      </h1>

      {/* 서브헤드 */}
      <p
        className="mx-auto mb-8 max-w-[540px]"
        style={{
          fontSize: 17,
          color: "var(--text-secondary)",
          lineHeight: 1.8,
        }}
      >
        팀의 대화, 노트, 자료가 CODE 파이프라인을 거치면 자동으로 구조화된
        지식이 됩니다. 세컨드 브레인의 가장 어려운 단계를 AI가 완전히
        자동화합니다.
      </p>

      {/* CTA 버튼 2개 */}
      <div className="flex flex-wrap items-center justify-center gap-2.5">
        <Link
          href="/sign-up"
          className="inline-flex cursor-pointer items-center justify-center rounded-lg px-6 font-semibold text-white transition-all active:scale-[0.97]"
          style={{
            fontFamily: "var(--font-display)",
            fontSize: 14,
            minHeight: 44,
            background: "var(--accent)",
            boxShadow: "0 2px 8px rgba(15,168,137,0.18)",
            borderRadius: "var(--radius-lg)",
          }}
        >
          무료로 시작하기
        </Link>
        <a
          href="#pipe"
          className="inline-flex cursor-pointer items-center justify-center rounded-lg px-6 font-semibold transition-all active:scale-[0.97]"
          style={{
            fontFamily: "var(--font-display)",
            fontSize: 14,
            minHeight: 44,
            background: "transparent",
            color: "var(--text-secondary)",
            border: "1.5px solid var(--border)",
            borderRadius: "var(--radius-lg)",
          }}
        >
          어떻게 작동하나요?
        </a>
      </div>

      {/* 신뢰 라인 */}
      <p
        className="mt-5"
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: 11,
          color: "var(--text-muted)",
        }}
      >
        설정 5분 &middot; 14일 무료 &middot; 신용카드 불필요
      </p>
    </section>
  );
}
