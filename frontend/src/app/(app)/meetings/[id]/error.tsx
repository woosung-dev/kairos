// 회의 상세 페이지 도메인 ErrorBoundary — STT/AI 처리 중 폴링 실패 / 권한 오류 격리
"use client";

import { useEffect } from "react";
import { trackError } from "@/lib/track-error";

export default function MeetingError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    trackError(error, { scope: "meetings/[id]", digest: error.digest });
  }, [error]);

  return (
    <div
      className="flex flex-col items-center justify-center min-h-[60vh] px-6 text-center"
      style={{ color: "var(--text-primary)" }}
    >
      <span className="text-5xl mb-6">🎙️</span>
      <h1
        className="text-xl font-bold mb-2"
        style={{ fontFamily: "var(--font-display)" }}
      >
        회의를 불러올 수 없습니다
      </h1>
      <p
        className="text-sm mb-6 max-w-md"
        style={{ color: "var(--text-muted)" }}
      >
        회의가 아직 처리 중이거나 (STT/AI) 삭제되었을 수 있습니다. 잠시 후 다시 시도하세요.
      </p>
      {error.digest && (
        <p className="text-micro mb-6" style={{ color: "var(--text-muted)" }}>
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
