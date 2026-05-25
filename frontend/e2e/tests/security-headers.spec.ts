// Sprint 27e BUG-S27e-TEST-1 — Sprint 27d BUG-S27d-4 보안 헤더 4종 회귀 가드 (FE).
// Sprint 27e Round 2 TEST-r2-1 — APIRequestContext 사용 (Node.js fetch, OS DNS) — CI
// chromium 의 ERR_NAME_NOT_RESOLVED 환경 quirk 회피. browser 페이지 렌더링 불필요 —
// HTTP HEAD/GET 응답 헤더만 검증.
import { expect, test } from "@playwright/test";

/**
 * frontend/next.config.ts:5-15 의 4종 보안 헤더가 모든 응답에 항상 포함되는지 검증.
 * 누군가 next.config.ts 의 headers() 를 정리하면 CI 가 즉시 감지.
 *
 * 검증 헤더:
 * - X-Frame-Options: DENY (clickjacking 방어)
 * - X-Content-Type-Options: nosniff (MIME sniffing 방어)
 * - Referrer-Policy: strict-origin-when-cross-origin (referer leak 방어)
 * - Permissions-Policy: camera=()… (browser feature 제한)
 */

const FOUR_HEADERS = [
  "x-frame-options",
  "x-content-type-options",
  "referrer-policy",
  "permissions-policy",
] as const;

test.describe("BUG-S27d-4 Security Headers Regression (Sprint 27e TEST-1)", () => {
  test("Sign-in / page returns 4 security headers", async ({ request }) => {
    // 비인증 사용자 진입점 — public 라우트. APIRequestContext = Node.js DNS, chromium 우회.
    const response = await request.get("/sign-in");
    expect(response).toBeTruthy();
    const headers = response.headers();

    for (const name of FOUR_HEADERS) {
      expect(headers[name], `${name} 헤더 누락 — BUG-S27d-4 회귀`).toBeTruthy();
    }
    expect(headers["x-frame-options"]).toBe("DENY");
    expect(headers["x-content-type-options"]).toBe("nosniff");
    expect(headers["referrer-policy"]).toBe("strict-origin-when-cross-origin");
    expect(headers["permissions-policy"]).toContain("camera=()");
  });

  test("Root / page returns 4 security headers", async ({ request }) => {
    const response = await request.get("/");
    expect(response).toBeTruthy();
    const headers = response.headers();

    for (const name of FOUR_HEADERS) {
      expect(headers[name], `${name} 헤더 누락 — BUG-S27d-4 회귀`).toBeTruthy();
    }
    expect(headers["x-frame-options"]).toBe("DENY");
    expect(headers["x-content-type-options"]).toBe("nosniff");
  });
});
