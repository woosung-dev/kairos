// Search 페이지 도메인 ErrorBoundary — RAG ask / 임베딩 검색 실패 격리
"use client";

import { useEffect } from "react";

export default function SearchError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // eslint-disable-next-line no-console
    console.error("[search error boundary]", error);
  }, [error]);

  return (
    <div
      className="flex flex-col items-center justify-center min-h-[60vh] px-6 text-center"
      style={{ color: "var(--text-primary)" }}
    >
      <span className="text-5xl mb-6">🔎</span>
      <h1
        className="text-xl font-bold mb-2"
        style={{ fontFamily: "var(--font-display)" }}
      >
        검색 결과를 불러올 수 없습니다
      </h1>
      <p
        className="text-sm mb-6 max-w-md"
        style={{ color: "var(--text-muted)" }}
      >
        RAG 임베딩 검색이 일시 장애일 수 있습니다. 다시 시도하거나 키워드를 단순화하세요.
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
