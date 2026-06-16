import { SignUp } from "@clerk/nextjs";

export default function SignUpPage() {
  return (
    <main
      id="main-content"
      className="flex flex-col items-center justify-center min-h-screen gap-4 px-4 py-12"
      style={{ background: "var(--background)" }}
    >
      {/* T-GTM-6 (Sprint 25): Pre-GA 베타 안내. dev Clerk 운영 정책 UX 완화 —
          가입 직전 사용자에게 "베타 멤버 전용 — Pre-GA" 명시로 30대 사용자 피싱
          의심 신호 완화 (BUG-CASUAL-001 정책 재분류 보완). */}
      <div
        className="max-w-md w-full rounded-lg px-4 py-3 text-center"
        style={{
          background: "var(--accent-subtle)",
          // P1 fix (2026-06-01): --accent-bd 는 [data-theme="landing"] 에만 정의 → (auth) 테마에서
          // 미해결로 border 미렌더. accent 기반 color-mix 로 교체(라이트/다크 공통 정의 토큰).
          border: "1px solid color-mix(in srgb, var(--accent) 25%, transparent)",
          borderRadius: "var(--radius-lg)",
        }}
      >
        <p
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: 12,
            color: "var(--accent)",
            letterSpacing: "0.02em",
            lineHeight: 1.6,
          }}
        >
          현재 베타 멤버 전용 — Pre-GA 단계입니다
        </p>
        <p
          className="mt-1"
          style={{
            fontSize: 12,
            color: "var(--text-secondary)",
            lineHeight: 1.65,
          }}
        >
          정식 출시 전 핵심 사용자와 함께 다듬는 중. 베타 기간 무료 + 우대 가격
          보장.
        </p>
      </div>

      <SignUp forceRedirectUrl="/dashboard" signInForceRedirectUrl="/dashboard" />
    </main>
  );
}
