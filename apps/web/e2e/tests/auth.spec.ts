// 인증 플로우 E2E — 미인증 리다이렉트 및 로그인 폼 렌더링 검증
import { test, expect } from "@playwright/test";

/**
 * Golden Path 0: 인증 플로우
 *
 * 검증 대상:
 * - 미인증 사용자가 /dashboard에 접근하면 /sign-in URL로 리다이렉트된다
 * - /sign-in 페이지에 이메일 입력 필드가 렌더링된다 (자체 로그인 폼)
 */

test.describe("인증 플로우", () => {
  // auth.setup.ts의 storageState를 비워서 미인증 상태로 실행
  test.use({ storageState: { cookies: [], origins: [] } });

  test("미인증 사용자는 /dashboard 접근 시 로그인 페이지로 이동한다", async ({
    page,
  }) => {
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/sign-in/);
  });

  test("로그인 페이지에 이메일 입력 필드가 렌더링된다", async ({ page }) => {
    await page.goto("/sign-in");
    // ADR-031: 셀렉터는 우리 폼의 data-testid 계약 (auth-form.tsx).
    // 예전 `input[name="identifier"]` 는 Clerk SDK 내부 규약이라 locale/버전에 취약했다.
    await expect(page.getByTestId("auth-email")).toBeVisible({
      timeout: 30_000,
    });
    await expect(page.getByTestId("auth-password")).toBeVisible();
    await expect(page.getByTestId("auth-google")).toBeVisible();
  });
});
