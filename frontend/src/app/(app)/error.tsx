"use client";

// (app) 그룹 ErrorBoundary — 페이지 trigger 에러를 graceful fallback 으로 처리
import { useEffect } from "react";
import { trackError } from "@/lib/track-error";

export default function AppError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    trackError(error, { scope: "(app)", digest: error.digest });
  }, [error]);

  return (
    <div
      className="flex flex-col items-center justify-center min-h-[60vh] px-6 text-center"
      style={{ color: "var(--text-primary)" }}
    >
      <span className="text-5xl mb-6">⚠️</span>
      <h1
        className="text-xl font-bold mb-2"
        style={{ fontFamily: "var(--font-display)" }}
      >
        문제가 발생했습니다
      </h1>
      <p
        className="text-sm mb-6 max-w-md"
        style={{ color: "var(--text-muted)" }}
      >
        잠시 후 다시 시도해주세요. 문제가 계속되면 새로고침하거나 다른 페이지로 이동하세요.
      </p>
      {error.digest && (
        <p className="text-[10px] mb-6" style={{ color: "var(--text-muted)" }}>
          digest: {error.digest}
        </p>
      )}
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
    </div>
  );
}
