// /pricing — 가격 페이지 (T-GTM-2 Pre-GA, "Pricing coming soon" 단일 메시지)
import Link from "next/link";
import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import { LandingNav } from "@/components/landing/landing-nav";
import { Footer } from "@/components/landing/footer";

export const metadata = {
  title: "가격 — Kairos",
  description: "베타 기간 무료. 정식 출시 시 베타 사용자 우대 가격 보장.",
};

export default async function PricingPage() {
  const { userId } = await auth();
  if (userId) {
    redirect("/dashboard");
  }

  return (
    <div style={{ background: "var(--background)", minHeight: "100vh" }}>
      <LandingNav />

      <main
        id="main-content"
        className="mx-auto max-w-[760px] px-6 pt-[152px] pb-16 text-center md:px-6"
        style={{ paddingTop: 152 }}
      >
        {/* 배지 — Beta */}
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
          Beta &middot; 2026
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
          가격 정책 준비 중
          <br />
          <span style={{ color: "var(--accent)" }}>베타 기간 무료</span>
        </h1>

        {/* 서브헤드 — T-UI-1 (Sprint 25): 모바일 16px, 데스크톱 17px 반응형 */}
        <p
          className="mx-auto mb-8 max-w-[560px]"
          style={{
            fontSize: "clamp(16px, 2.5vw, 17px)",
            color: "var(--text-secondary)",
            lineHeight: 1.8,
          }}
        >
          Kairos는 한국팀을 위한 세컨드 브레인입니다. 정식 가격 공개 전까지
          모든 기능을 무료로 사용하실 수 있으며, 베타 사용자에게는 정식 출시
          후에도 우대 가격을 보장합니다.
        </p>

        {/* CTA */}
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
            베타로 시작하기
          </Link>
          <Link
            href="/"
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
            홈으로
          </Link>
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
          신용카드 불필요 &middot; 설정 5분 &middot; 베타 우대 가격 보장
        </p>

        {/* FAQ 미니 카드 — 가격 공개 시점 */}
        <section
          className="mx-auto mt-16 max-w-[560px] rounded-2xl px-6 py-8 text-left"
          style={{
            background: "var(--surface)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "var(--radius-lg)",
          }}
        >
          <h2
            className="mb-3"
            style={{
              fontFamily: "var(--font-display)",
              fontSize: 18,
              fontWeight: 700,
              color: "var(--text-primary)",
            }}
          >
            정식 가격은 언제 공개되나요?
          </h2>
          <p
            style={{
              fontSize: 14,
              color: "var(--text-secondary)",
              lineHeight: 1.7,
            }}
          >
            베타 사용자 피드백을 충분히 반영한 뒤 합리적인 가격으로 공개할
            예정입니다. 베타로 가입하시면 정식 출시 시 가장 먼저 알림을
            받으시며, 베타 우대 가격이 자동 적용됩니다.
          </p>
        </section>
      </main>

      <Footer />
    </div>
  );
}
