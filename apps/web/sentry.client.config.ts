// 브라우저 측 Sentry 초기화 — 클라이언트 에러 추적
import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  sendDefaultPii: false,
  tracesSampleRate: 0.1,
  // ADR-028: Vercel 이탈로 NEXT_PUBLIC_VERCEL_ENV 가 사라진다. 병행 기간 동안은
  // Vercel 빌드도 라벨을 유지해야 하므로 fallback 체인을 둔다 (컷오버 후 Vercel 항 제거).
  environment:
    process.env.NEXT_PUBLIC_APP_ENV ??
    process.env.NEXT_PUBLIC_VERCEL_ENV ??
    "development",
  beforeSend(event) {
    if (event.user) {
      delete event.user.email;
      delete event.user.ip_address;
    }
    return event;
  },
});
