import Link from "next/link";

export default function LandingPage() {
  return (
    <div
      className="flex flex-col items-center justify-center min-h-screen px-4"
      style={{ background: "var(--background)" }}
    >
      <div className="text-center max-w-2xl">
        {/* 로고 */}
        <h1
          className="text-6xl font-bold mb-4"
          style={{ fontFamily: "var(--font-display)", color: "var(--text-primary)" }}
        >
          Kairos
        </h1>

        {/* 부제 */}
        <p
          className="text-xl mb-2"
          style={{ fontFamily: "var(--font-display)", color: "var(--accent)" }}
        >
          팀의 세컨드 브레인
        </p>

        {/* 설명 */}
        <p
          className="text-base mb-10"
          style={{ color: "var(--text-secondary)" }}
        >
          회의, 노트, 자료가 쌓일수록 조직이 똑똑해집니다
        </p>

        {/* CTA */}
        <div className="flex items-center justify-center gap-4">
          <Link
            href="/sign-up"
            className="px-6 py-3 rounded font-medium text-sm transition-colors"
            style={{
              background: "var(--accent)",
              color: "var(--background)",
              borderRadius: "var(--radius-sm)",
            }}
          >
            시작하기
          </Link>
          <Link
            href="/sign-in"
            className="px-6 py-3 rounded font-medium text-sm transition-colors border"
            style={{
              borderColor: "var(--border)",
              color: "var(--text-secondary)",
              borderRadius: "var(--radius-sm)",
            }}
          >
            로그인
          </Link>
        </div>
      </div>
    </div>
  );
}
