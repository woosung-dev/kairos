// 프로젝트 상세 페이지 도메인 ErrorBoundary — 한 프로젝트 에러가 (app) 전체로 번지지 않도록 격리
"use client";

import { useEffect } from "react";

export default function ProjectError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // eslint-disable-next-line no-console
    console.error("[projects/[id] error boundary]", error);
  }, [error]);

  return (
    <div
      className="flex flex-col items-center justify-center min-h-[60vh] px-6 text-center"
      style={{ color: "var(--text-primary)" }}
    >
      <span className="text-5xl mb-6">📁</span>
      <h1
        className="text-xl font-bold mb-2"
        style={{ fontFamily: "var(--font-display)" }}
      >
        프로젝트를 불러올 수 없습니다
      </h1>
      <p
        className="text-sm mb-6 max-w-md"
        style={{ color: "var(--text-muted)" }}
      >
        프로젝트가 삭제되었거나 접근 권한이 없을 수 있습니다. 다시 시도하거나 프로젝트 목록으로 이동하세요.
      </p>
      {error.digest && (
        <p className="text-[10px] mb-6" style={{ color: "var(--text-muted)" }}>
          digest: {error.digest}
        </p>
      )}
      <div className="flex gap-3">
        <button
          type="button"
          onClick={reset}
          className="px-5 py-2.5 rounded text-sm font-medium transition-colors"
          style={{
            background: "var(--accent)",
            color: "var(--background)",
            borderRadius: "var(--radius-sm)",
            minHeight: 44,
            cursor: "pointer",
          }}
        >
          다시 시도
        </button>
        <a
          href="/dashboard"
          className="px-5 py-2.5 rounded text-sm font-medium transition-colors inline-flex items-center"
          style={{
            background: "var(--surface)",
            color: "var(--text-primary)",
            borderRadius: "var(--radius-sm)",
            borderColor: "var(--border)",
            borderWidth: 1,
            minHeight: 44,
          }}
        >
          대시보드로
        </a>
      </div>
    </div>
  );
}
