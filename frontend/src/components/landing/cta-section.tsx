"use client";

import Link from "next/link";
import { useReveal } from "@/hooks/use-reveal";

export function CtaSection() {
  const ref = useReveal<HTMLElement>();

  return (
    <section
      ref={ref}
      id="cta"
      className="landing-reveal mx-auto max-w-[600px] px-6 pb-[120px] text-center"
    >
      <div
        className="rounded-2xl px-9 py-12 text-white"
        style={{
          background: "var(--cta-box-bg)",
          borderRadius: 16,
          padding: "48px 36px",
          boxShadow: "0 8px 32px rgba(0,0,0,0.1)",
        }}
      >
        <h2
          className="mb-3"
          style={{
            fontFamily: "var(--font-display)",
            fontSize: 26,
            fontWeight: 700,
            color: "#fff",
          }}
        >
          팀의 세컨드 브레인을
          <br />
          지금 구축하세요
        </h2>

        <p
          className="mb-7"
          style={{
            fontSize: 15,
            lineHeight: 1.7,
            // T-A11Y-1 (Sprint 25): #94A3B8 → #CBD5E1 (slate-300) 상향. WCAG AA
            // 4.5:1 대비 충족 (dark CTA box 배경 대비 슬레이트-400 borderline).
            color: "#CBD5E1",
          }}
        >
          베타 무료 &middot; 신용카드 불필요 &middot; 5분 설정
          <br />
          팀의 첫 인사이트는 24시간 이내에.
        </p>

        <Link
          href="/sign-up"
          className="inline-flex cursor-pointer items-center justify-center rounded-lg px-9 font-semibold transition-all active:scale-[0.97]"
          style={{
            fontFamily: "var(--font-display)",
            fontSize: 15,
            minHeight: 44,
            background: "var(--cta-box-btn-bg)",
            color: "var(--cta-box-btn-color)",
            borderRadius: "var(--radius-lg)",
            border: "none",
          }}
        >
          무료 체험 시작
        </Link>

        <div
          className="mt-3.5"
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: 11,
            // T-A11Y-1 (Sprint 25): #5C5C63 → #94A3B8 상향. dark 배경 대비
            // 4.5:1 미달 회피 (지표/캡션 텍스트도 WCAG AA 권고).
            color: "#94A3B8",
          }}
        >
          Google 워크스페이스 연동 &middot; 팀 초대 무제한
        </div>
      </div>
    </section>
  );
}
