// 신뢰 신호 섹션 — Pre-GA Beta 단계 솔직한 인프라/정책 transparency (T-GTM-1)
"use client";

import { Database, ShieldCheck, Sparkles } from "lucide-react";
import { useReveal } from "@/hooks/use-reveal";

type TrustItem = {
  icon: typeof ShieldCheck;
  title: string;
  description: string;
};

const ITEMS: TrustItem[] = [
  {
    icon: ShieldCheck,
    title: "Built on 검증된 인프라",
    description:
      "Clerk 인증 · Neon PostgreSQL · Cloudflare R2 스토리지 · Google Cloud Run. 직접 운영하지 않는 모든 계층을 신뢰할 수 있는 SaaS로 위임합니다.",
  },
  {
    icon: Database,
    title: "데이터는 항상 당신의 것",
    description:
      "회의·노트·요약 모두 Markdown / JSON 으로 즉시 export. Lock-in 없이 떠날 수 있어야 머무를 수 있다고 믿습니다.",
  },
  {
    icon: Sparkles,
    title: "Pre-GA 베타 — 솔직한 단계 공개",
    description:
      "지금은 초기 사용자와 함께 다듬는 베타 시기입니다. 기능 변경·이슈는 dev-log로 투명하게 기록하며, 베타 사용자의 의견이 우선순위 1번입니다.",
  },
];

export function TrustSignalsSection() {
  const ref = useReveal<HTMLElement>();

  return (
    <section
      ref={ref}
      id="trust"
      className="landing-reveal mx-auto max-w-[960px] px-6 py-16 md:px-6"
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
        믿고 맡겨도 되는 이유
      </h2>
      <p
        className="mx-auto mb-12 max-w-[560px] text-center"
        style={{
          fontSize: 15,
          color: "var(--text-secondary)",
          lineHeight: 1.7,
        }}
      >
        과장된 사회적 증명 대신, 실제로 우리가 어떻게 운영하는지 공개합니다.
      </p>

      {/* 3 신호 카드 */}
      <div className="grid grid-cols-1 gap-5 md:grid-cols-3 md:gap-6">
        {ITEMS.map((item) => {
          const Icon = item.icon;
          return (
            <article
              key={item.title}
              className="rounded-2xl p-6"
              style={{
                background: "var(--surface)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "var(--radius-lg)",
              }}
            >
              <div
                className="mb-4 inline-flex items-center justify-center rounded-full"
                style={{
                  width: 40,
                  height: 40,
                  background: "var(--accent-subtle)",
                  color: "var(--accent)",
                }}
                aria-hidden="true"
              >
                <Icon size={20} strokeWidth={2} />
              </div>
              <h3
                className="mb-2"
                style={{
                  fontFamily: "var(--font-display)",
                  fontSize: 16,
                  fontWeight: 700,
                  color: "var(--text-primary)",
                  letterSpacing: "-0.015em",
                }}
              >
                {item.title}
              </h3>
              <p
                style={{
                  fontSize: 13.5,
                  color: "var(--text-secondary)",
                  lineHeight: 1.65,
                }}
              >
                {item.description}
              </p>
            </article>
          );
        })}
      </div>

      {/* Built with 마이크로카피 */}
      <p
        className="mt-10 text-center"
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: 11,
          color: "var(--text-muted)",
          letterSpacing: "0.02em",
        }}
      >
        Built with Clerk &middot; Neon &middot; Cloudflare R2 &middot; Google
        Cloud &middot; Vercel
      </p>
    </section>
  );
}
