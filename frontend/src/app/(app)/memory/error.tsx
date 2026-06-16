// Memory 페이지 도메인 ErrorBoundary — Capture/Recall/Promote API 실패 격리
"use client";

import { useEffect } from "react";
import { Brain } from "lucide-react";
import { trackError } from "@/lib/track-error";

export default function MemoryError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    trackError(error, { scope: "memory", digest: error.digest });
  }, [error]);

  return (
    <div
      className="flex flex-col items-center justify-center min-h-[60vh] px-6 text-center"
      style={{ color: "var(--text-primary)" }}
    >
      <Brain className="w-12 h-12 mb-6" style={{ color: "var(--text-muted)" }} />
      <h1
        className="text-xl font-bold mb-2"
        style={{ fontFamily: "var(--font-display)" }}
      >
        Memory 를 불러올 수 없습니다
      </h1>
      <p
        className="text-sm mb-6 max-w-md"
        style={{ color: "var(--text-muted)" }}
      >
        recall / promote 처리가 지연되었거나 일시적 오류일 수 있습니다. 이미 저장된 메모는 안전합니다.
      </p>
      {error.digest && (
        <p className="text-micro mb-6" style={{ color: "var(--text-muted)" }}>
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
