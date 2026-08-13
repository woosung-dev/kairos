export default function NotFound() {
  // F-2C v2 (Sprint 25 polish, agy 발견): skip-link 타깃 누락. 외각 div → main.
  return (
    <main
      id="main-content"
      className="flex items-center justify-center min-h-screen"
      style={{ background: "var(--background)" }}
    >
      <div className="text-center">
        <h1
          className="text-6xl font-bold mb-4"
          style={{ fontFamily: "var(--font-display)", color: "var(--text-muted)" }}
        >
          404
        </h1>
        <p style={{ color: "var(--text-secondary)" }}>페이지를 찾을 수 없습니다</p>
        <a
          href="/"
          className="mt-4 inline-block"
          style={{ color: "var(--accent)" }}
        >
          홈으로 돌아가기
        </a>
      </div>
    </main>
  );
}
