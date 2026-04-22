import { test as setup, expect } from "@playwright/test";
import path from "node:path";

/**
 * Clerk 로그인 setup — storageState 를 저장해 테스트 간 재로그인 비용을 없앤다.
 *
 * 전략: Clerk dev 인스턴스의 테스트 계정 이메일 + OTP (testing mode 고정값).
 *
 * 필요 env (GitHub Secrets · 로컬 .env.local):
 *   E2E_USER_EMAIL          — Clerk dev 인스턴스에 사전 생성된 테스트 계정 이메일
 *   E2E_USER_OTP            — Clerk testing mode 고정 OTP (예: 424242)
 *
 * Clerk testing mode:
 *   Clerk dashboard → Configure → Testing → "Enable testing mode" 활성화 시
 *   특정 이메일 도메인·특정 OTP 조합이 항상 통과. 상세는 Clerk 공식 문서 참조.
 */

const AUTH_FILE = path.join(__dirname, ".auth/user.json");

setup("authenticate", async ({ page }) => {
  const email = process.env.E2E_USER_EMAIL;
  const otp = process.env.E2E_USER_OTP;

  if (!email || !otp) {
    throw new Error(
      "E2E_USER_EMAIL · E2E_USER_OTP 환경변수가 필요합니다. " +
        "Clerk dashboard에서 testing mode + 테스트 계정을 생성한 뒤 .env.local 또는 GitHub Secrets에 등록하세요.",
    );
  }

  await page.goto("/sign-in");

  // Clerk 기본 이메일 입력
  await page.getByLabel(/email/i).fill(email);
  await page.getByRole("button", { name: /continue|계속/i }).click();

  // OTP 입력 (6자리 분할 입력 위젯)
  const otpInputs = page.locator('input[aria-label*="digit" i], input[name^="code"]');
  const count = await otpInputs.count();
  if (count === 1) {
    await otpInputs.first().fill(otp);
  } else {
    for (let i = 0; i < otp.length && i < count; i++) {
      await otpInputs.nth(i).fill(otp[i]);
    }
  }

  // Clerk가 대시보드로 리다이렉트할 때까지 대기
  await page.waitForURL(/\/dashboard/, { timeout: 20_000 });
  await expect(page.getByText(/오늘의 Kairos|무엇이든 질문하세요/)).toBeVisible();

  // 세션 스토리지 + 쿠키 저장
  await page.context().storageState({ path: AUTH_FILE });
});
