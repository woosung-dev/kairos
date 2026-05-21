"use client";

import Link from "next/link";

export function LandingNav() {
  return (
    <nav
      className="fixed top-0 right-0 left-0 z-50 flex items-center justify-between px-8 py-3.5 md:px-8"
      style={{
        background: "color-mix(in srgb, var(--background) 88%, transparent)",
        backdropFilter: "blur(12px)",
        WebkitBackdropFilter: "blur(12px)",
        borderBottom: "1px solid var(--border-subtle)",
        padding: "14px 32px",
      }}
    >
      {/* 로고 */}
      <Link
        href="/"
        style={{
          fontFamily: "var(--font-display)",
          fontWeight: 700,
          fontSize: 18,
          color: "var(--text-primary)",
        }}
      >
        Kairos
      </Link>

      {/* 오른쪽 */}
      <div className="flex items-center gap-5">
        <a
          href="#pipe"
          className="hidden cursor-pointer transition-colors sm:block"
          style={{
            fontSize: 13,
            color: "var(--text-secondary)",
          }}
        >
          기능
        </a>
        <Link
          href="/pricing"
          className="hidden cursor-pointer transition-colors sm:block"
          style={{
            fontSize: 13,
            color: "var(--text-secondary)",
          }}
        >
          요금
        </Link>
        <Link
          href="/sign-in"
          className="cursor-pointer transition-colors"
          style={{
            fontSize: 13,
            color: "var(--text-secondary)",
          }}
        >
          로그인
        </Link>
        <Link
          href="/sign-up"
          className="inline-flex cursor-pointer items-center justify-center rounded-lg font-semibold text-white transition-all active:scale-[0.97]"
          style={{
            fontFamily: "var(--font-display)",
            fontSize: 13,
            minHeight: 36,
            padding: "0 16px",
            background: "var(--accent)",
            borderRadius: "var(--radius-lg)",
          }}
        >
          시작하기
        </Link>
      </div>
    </nav>
  );
}
