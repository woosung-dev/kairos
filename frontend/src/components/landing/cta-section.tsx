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
            color: "#94A3B8",
          }}
        >
          14일 무료 &middot; 신용카드 불필요 &middot; 5분 설정
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
            color: "#5C5C63",
          }}
        >
          Google 워크스페이스 연동 &middot; 팀 초대 무제한
        </div>
      </div>
    </section>
  );
}
