import Link from "next/link";

export function HeroSection() {
  return (
    <section
      className="min-h-screen flex flex-col items-center justify-center px-6 pt-20"
      style={{ background: "var(--background)" }}
    >
      {/* 배지 */}
      <div
        className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-sm mb-8"
        style={{
          background: "var(--accent-subtle)",
          color: "var(--accent)",
          borderRadius: "var(--radius-full)",
          fontFamily: "var(--font-body)",
        }}
      >
        <span
          className="w-2 h-2 rounded-full"
          style={{ background: "var(--accent)" }}
        />
        오픈 베타 — 지금 무료로 시작하세요
      </div>

      {/* 헤드라인 */}
      <h1
        className="text-center mb-6"
        style={{
          fontFamily: "var(--font-display)",
          fontWeight: 700,
          fontSize: "clamp(36px, 5vw, 56px)",
          lineHeight: 1.15,
          color: "var(--text-primary)",
          letterSpacing: "-0.02em",
        }}
      >
        회의가 끝나면,
        <br />
        지식이 시작됩니다
      </h1>

      {/* 서브헤드 */}
      <p
        className="text-center max-w-xl mb-10"
        style={{
          fontFamily: "var(--font-body)",
          fontSize: "18px",
          lineHeight: 1.7,
          color: "var(--text-secondary)",
        }}
      >
        Kairos는 회의 녹음, 노트, 자료를 AI가 자동으로 구조화하고
        <br className="hidden sm:block" />
        필요할 때 즉시 찾아주는 팀의 세컨드 브레인입니다
      </p>

      {/* CTA */}
      <div className="flex items-center gap-4 mb-16">
        <Link
          href="/sign-up"
          className="px-6 py-3 rounded text-sm font-semibold transition-opacity hover:opacity-90"
          style={{
            background: "var(--accent)",
            color: "#FFFFFF",
            borderRadius: "var(--radius-sm)",
          }}
        >
          무료로 시작하기
        </Link>
        <a
          href="#demo"
          className="px-6 py-3 rounded text-sm font-medium border transition-colors"
          style={{
            borderColor: "var(--border)",
            color: "var(--text-secondary)",
            borderRadius: "var(--radius-sm)",
          }}
        >
          제품 둘러보기 →
        </a>
      </div>

      {/* 기하학적 장식 */}
      <div className="relative w-full max-w-3xl h-32 opacity-30">
        <div
          className="absolute left-1/2 -translate-x-1/2 w-[400px] h-[400px] rounded-full"
          style={{
            background: `radial-gradient(circle, var(--accent-subtle) 0%, transparent 70%)`,
          }}
        />
      </div>
    </section>
  );
}
