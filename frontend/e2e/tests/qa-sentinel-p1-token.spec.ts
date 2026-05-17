// Sentinel-P1 단일 토큰 추출 헬퍼 — Sentinel A JWT 발급 후 /tmp/qa-jwt-sentinel-a.txt 저장
/**
 * Sprint 18 → 19 Sentinel-P1 검증용 fresh JWT 추출.
 * 한 번 실행 → /tmp/qa-jwt-sentinel-a.txt 에 JWT 저장.
 * 60초 만료이므로 즉시 curl 검증에 사용.
 *
 * 사용: QA_PASSWORD='xxx' pnpm exec playwright test e2e/tests/qa-sentinel-p1-token.spec.ts
 *
 * 본 spec 은 Sprint 18→19 Step 5 의 임시 헬퍼. Step 6 이후 삭제 권장.
 */
import { test, expect } from "@playwright/test";
import * as fs from "node:fs";

const PASSWORD = process.env.QA_PASSWORD ?? "";
if (!PASSWORD) throw new Error("QA_PASSWORD 미설정");

test.use({ storageState: { cookies: [], origins: [] } });

test("Sentinel-P1: extract fresh JWT for Sentinel A", async ({ page }) => {
  test.setTimeout(60_000);
  await page.goto("/sign-in");
  await page.locator('input[name="identifier"]').fill("wkddntjd3429@naver.com");
  await page.getByRole("button", { name: /continue|계속/i }).click();
  await page.locator('input[type="password"]').fill(PASSWORD);
  await page.getByRole("button", { name: /continue|sign in|로그인|계속/i }).click();
  await page.waitForURL(/\/dashboard|\/$/, { timeout: 30_000 });

  const token: string | null = await page.evaluate(async () => {
    // @ts-expect-error Clerk SDK global
    const clerk = window?.Clerk;
    if (!clerk?.session) return null;
    return await clerk.session.getToken();
  });
  expect(token).toBeTruthy();
  fs.writeFileSync("/tmp/qa-jwt-sentinel-a.txt", token!);
  console.log(`[SENTINEL_A] JWT 저장: /tmp/qa-jwt-sentinel-a.txt (length=${token!.length})`);
});
