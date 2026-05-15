// (app) 그룹 Suspense fallback — Server Component pending 시 표시
export default function AppLoading() {
  return (
    <div
      className="flex items-center justify-center min-h-[60vh]"
      style={{ color: "var(--text-muted)" }}
    >
      <div className="flex items-center gap-3">
        <div
          className="w-4 h-4 rounded-full animate-pulse"
          style={{ background: "var(--accent)" }}
        />
        <span className="text-sm">불러오는 중...</span>
      </div>
    </div>
  );
}
