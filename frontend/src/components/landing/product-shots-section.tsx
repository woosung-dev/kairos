// 실 제품 스크린샷 섹션 — vaporware 의심 해소 (T-GTM-3, ★★ PRODUCT-SHOT)
"use client";

import Image from "next/image";
import { useReveal } from "@/hooks/use-reveal";

type ProductShot = {
  src: string;
  alt: string;
  title: string;
  caption: string;
};

const SHOTS: ProductShot[] = [
  {
    src: "/landing/screenshots/screenshot-rag-answer.png",
    alt: "Kairos Cmd+K 지식 검색 패널 — 회의 결정사항을 묻고 출처와 함께 답을 받는 화면",
    title: "출처와 함께 답을 받는 Cmd+K",
    caption:
      "팀의 회의·노트·자료에서 곧바로 검색. 모든 답엔 출처가 따라옵니다.",
  },
  {
    src: "/landing/screenshots/screenshot-meeting-summary.png",
    alt: "Kairos 회의 자동 요약 — 요약/핵심 결정사항/주제 태그가 자동 정리된 화면",
    title: "회의 끝나면 요약이 먼저 와있습니다",
    caption:
      "Distill — 요약 · 핵심 결정사항 · 주제 자동 추출. 받아쓰는 시간은 0분.",
  },
  {
    src: "/landing/screenshots/screenshot-dashboard.png",
    alt: "Kairos 대시보드 홈 — 추천 질문과 빠른 접근(회의 추가/노트/Inbox/프로젝트) 화면",
    title: "한 화면에 두는 팀의 두뇌",
    caption:
      "회의·노트·Inbox·프로젝트가 한 화면에 정리됩니다. 흩어진 SaaS를 모읍니다.",
  },
];

export function ProductShotsSection() {
  const ref = useReveal<HTMLElement>();

  return (
    <section
      ref={ref}
      id="shots"
      className="landing-reveal mx-auto max-w-[1080px] px-6 py-16 md:px-6"
    >
      {/* 섹션 헤드 */}
      <h2
        className="mb-3 text-center"
        style={{
          fontFamily: "var(--font-display)",
          fontSize: "clamp(24px, 3.5vw, 32px)",
          fontWeight: 800,
          letterSpacing: "-0.025em",
          color: "var(--text-primary)",
        }}
      >
        이미 동작하는 제품입니다
      </h2>
      <p
        className="mx-auto mb-12 max-w-[560px] text-center"
        style={{
          fontSize: 15,
          color: "var(--text-secondary)",
          lineHeight: 1.7,
        }}
      >
        목업이 아닙니다. 베타 사용자가 실제로 보는 화면 그대로입니다.
      </p>

      <div className="grid grid-cols-1 gap-10 md:gap-14">
        {SHOTS.map((shot, idx) => (
          <article
            key={shot.src}
            className={`flex flex-col items-center gap-6 md:flex-row md:items-center md:gap-10 ${
              idx % 2 === 1 ? "md:flex-row-reverse" : ""
            }`}
          >
            {/* 스크린샷 */}
            <div
              className="w-full max-w-[600px] overflow-hidden md:flex-1"
              style={{
                borderRadius: "var(--radius-lg)",
                border: "1px solid var(--border-subtle)",
                boxShadow: "0 8px 32px rgba(0, 0, 0, 0.16)",
                background: "var(--surface)",
              }}
            >
              <Image
                src={shot.src}
                alt={shot.alt}
                width={1720}
                height={1280}
                sizes="(max-width: 768px) 100vw, 600px"
                style={{
                  width: "100%",
                  height: "auto",
                  display: "block",
                }}
                priority={idx === 0}
              />
            </div>

            {/* 카피 */}
            <div className="md:flex-1 md:max-w-[400px]">
              <h3
                className="mb-3"
                style={{
                  fontFamily: "var(--font-display)",
                  fontSize: "clamp(20px, 3vw, 26px)",
                  fontWeight: 800,
                  lineHeight: 1.2,
                  letterSpacing: "-0.02em",
                  color: "var(--text-primary)",
                }}
              >
                {shot.title}
              </h3>
              <p
                style={{
                  fontSize: 15,
                  color: "var(--text-secondary)",
                  lineHeight: 1.7,
                }}
              >
                {shot.caption}
              </p>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
