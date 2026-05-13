import { test as setup, expect } from "@playwright/test";
import path from "node:path";

/**
 * Clerk 로그인 setup — storageState 를 저장해 테스트 간 재로그인 비용을 없앤다.
 *
 * 전략: Clerk dev 인스턴스의 테스트 계정 이메일 + 비밀번호.
 *
 * 필요 env (GitHub Secrets · 로컬 .env.local):
 *   E2E_USER_EMAIL     — Clerk dev 인스턴스에 사전 생성된 테스트 계정 이메일
 *   E2E_USER_PASSWORD  — 해당 계정 비밀번호
 */

const AUTH_FILE = path.join(__dirname, ".auth/user.json");

setup("authenticate", async ({ page }) => {
  const email = process.env.E2E_USER_EMAIL;
  const password = process.env.E2E_USER_PASSWORD;

  if (!email || !password) {
    throw new Error(
      "E2E_USER_EMAIL · E2E_USER_PASSWORD 환경변수가 필요합니다. " +
        ".env.local 또는 GitHub Secrets에 테스트 계정 정보를 등록하세요.",
    );
  }

  await page.goto("/sign-in");

  // 이메일 입력
  await page.getByLabel(/email/i).fill(email);
  await page.getByRole("button", { name: /continue|계속/i }).click();

  // 비밀번호 입력
  await page.locator('input[type="password"]').fill(password);
  await page.getByRole("button", { name: /continue|sign in|로그인|계속/i }).click();

  // Clerk가 대시보드로 리다이렉트할 때까지 대기
  await page.waitForURL(/\/dashboard/, { timeout: 20_000 });
  // 페이지 로드 완료 대기 (CI 환경에서 렌더링 지연 대응)
  await page.waitForLoadState("networkidle");

  // 세션 스토리지 + 쿠키 저장
  await page.context().storageState({ path: AUTH_FILE });
});
