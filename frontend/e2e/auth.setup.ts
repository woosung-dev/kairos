import { test as setup } from "@playwright/test";
import path from "node:path";

/**
 * Clerk 로그인 setup — storageState 를 저장해 테스트 간 재로그인 비용을 없앤다.
 *
 * 전략: Clerk dev 인스턴스의 테스트 계정 이메일 + 비밀번호.
 * 로그인 후 워크스페이스가 없으면 자동 생성 (CI 최초 실행 대응).
 *
 * 필요 env:
 *   E2E_USER_EMAIL     — 테스트 계정 이메일
 *   E2E_USER_PASSWORD  — 테스트 계정 비밀번호
 *   E2E_API_URL        — 백엔드 API URL
 */

const AUTH_FILE = path.join(__dirname, ".auth/user.json");

setup("authenticate", async ({ page }) => {
  const email = process.env.E2E_USER_EMAIL;
  const password = process.env.E2E_USER_PASSWORD;
  const apiUrl = process.env.E2E_API_URL ?? "http://localhost:8000";

  if (!email || !password) {
    throw new Error(
      "E2E_USER_EMAIL · E2E_USER_PASSWORD 환경변수가 필요합니다.",
    );
  }

  await page.goto("/sign-in");

  // 이메일 입력
  await page.getByLabel(/email/i).fill(email);
  await page.getByRole("button", { name: /continue|계속/i }).click();

  // 비밀번호 입력
  await page.locator('input[type="password"]').fill(password);
  await page.getByRole("button", { name: /continue|sign in|로그인|계속/i }).click();

  // /dashboard 리다이렉트 = 로그인 성공
  await page.waitForURL(/\/dashboard/, { timeout: 20_000 });

  // 워크스페이스 없으면 API로 자동 생성 (CI 최초 실행 대응)
  const token = await page.evaluate(async () => {
    // @ts-ignore
    return await window?.Clerk?.session?.getToken?.() ?? null;
  });

  if (token) {
    const wsRes = await page.request.get(`${apiUrl}/api/v1/workspaces`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const workspaces = await wsRes.json().catch(() => []);
    const wsList = Array.isArray(workspaces) ? workspaces : [];

    if (wsList.length === 0) {
      await page.request.post(`${apiUrl}/api/v1/workspaces`, {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        data: { name: "E2E 테스트 워크스페이스" },
      });
      // 워크스페이스 생성 후 대시보드 재로드
      await page.goto("/dashboard");
      await page.waitForURL(/\/dashboard/, { timeout: 20_000 });
    }
  }

  // 세션 스토리지 + 쿠키 저장
  await page.context().storageState({ path: AUTH_FILE });
});
