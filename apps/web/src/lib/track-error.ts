// 에러 추적 통합 entry point — Sentry/Datadog 등 외부 추적 SDK 도입 시 한 곳만 교체
//
// 현재: console.error 만. Sentry DSN 환경변수 추가 시 본 모듈에 init + capture 호출만 추가하면
// 호출처 (5 ErrorBoundary + 향후 page-level catch) 변경 없이 추적 활성화.

export interface ErrorContext {
  /** 호출 측면 — 도메인/페이지 이름 (예: "memory", "projects/[id]") */
  scope: string;
  /** Next.js error.tsx 의 digest 등 ID */
  digest?: string;
  /** 추가 구조화 메타 (사용자 id 등 PII 제외) */
  extra?: Record<string, unknown>;
}

/** ErrorBoundary 및 catch 블록에서 호출. Sentry 도입 시 본 함수에 captureException 추가. */
export function trackError(error: unknown, context: ErrorContext): void {
  const payload = {
    scope: context.scope,
    digest: context.digest,
    extra: context.extra,
    error:
      error instanceof Error
        ? { name: error.name, message: error.message, stack: error.stack }
        : error,
    timestamp: new Date().toISOString(),
  };

  // eslint-disable-next-line no-console
  console.error(`[track-error] ${context.scope}`, payload);

  // Sentry/Datadog 도입 시 여기에 추가:
  //   if (typeof window !== "undefined" && window.Sentry) {
  //     window.Sentry.captureException(error, { tags: { scope: context.scope }, extra: payload });
  //   }
}
