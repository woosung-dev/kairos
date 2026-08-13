// Inbox 페이지 도메인 ErrorBoundary — AI classify / Suggestion API 실패 격리
"use client";

import { useEffect } from "react";
import { Inbox } from "lucide-react";
import { trackError } from "@/lib/track-error";

export default function InboxError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    trackError(error, { scope: "inbox", digest: error.digest });
  }, [error]);

  return (
    <div
      className="flex flex-col items-center justify-center min-h-[60vh] px-6 text-center"
      style={{ color: "var(--text-primary)" }}
    >
      <Inbox className="w-12 h-12 mb-6" style={{ color: "var(--text-muted)" }} />
      <h1
        className="text-xl font-bold mb-2"
        style={{ fontFamily: "var(--font-display)" }}
      >
        Inbox 를 불러올 수 없습니다
      </h1>
      <p
        className="text-sm mb-6 max-w-md"
        style={{ color: "var(--text-muted)" }}
      >
        AI 분류 서버 일시 장애일 수 있습니다. 다시 시도하거나 새 항목 추가는 그대로 가능합니다.
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
