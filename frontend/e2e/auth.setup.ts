import { test as setup } from "@playwright/test";
import path from "node:path";

/**
 * Clerk 로그인 + 워크스페이스 보장 setup.
 * 저장된 storageState (cookies + localStorage)를 이후 테스트들이 재사용.
 *
 * 동작:
 *   1) Clerk dev 인스턴스에 email/password 로그인
 *   2) /api/v1/workspaces로 워크스페이스 보장 (없으면 생성)
 *   3) localStorage.kairos-workspace에 activeWorkspaceId 주입
 *      → 다른 페이지(/new, /search 등)에서 워크스페이스 컨텍스트를 즉시 사용 가능
 *
 * CORS 주의:
 *   localhost FE → 프로덕션 BE 호출은 CORS preflight에서 차단됨.
 *   playwright.config.ts의 launchOptions에 --disable-web-security가 설정되어 있어야 함.
 *
 * 필요 env:
 *   E2E_USER_EMAIL, E2E_USER_PASSWORD, E2E_API_URL
 */

const AUTH_FILE = path.join(__dirname, ".auth/user.json");

setup("authenticate", async ({ page }) => {
  setup.setTimeout(60_000);

  const email = process.env.E2E_USER_EMAIL;
  const password = process.env.E2E_USER_PASSWORD;
  const apiUrl = process.env.E2E_API_URL ?? "http://localhost:8000";

  if (!email || !password) {
    throw new Error(
      "E2E_USER_EMAIL · E2E_USER_PASSWORD 환경변수가 필요합니다.",
    );
  }

  // ── Clerk 로그인 ──
  // BL-021 fix: Clerk koKR localization (Sprint 14 9ea1a78) 후 label "이메일 주소"로 변경.
  // 영문 정규식 `/email/i` 매치 실패 → 60s timeout regression.
  // Clerk SDK standard input `name="identifier"` 사용 — locale 변화 무관.
  await page.goto("/sign-in");
  await page.locator('input[name="identifier"]').fill(email);
  await page.getByRole("button", { name: /continue|계속/i }).click();
  await page.locator('input[type="password"]').fill(password);
  await page.getByRole("button", { name: /continue|sign in|로그인|계속/i }).click();
  await page.waitForURL(/\/dashboard/, { timeout: 30_000 });

  // ── 워크스페이스 보장 (API 직접 호출) ──
  const token: string | null = await page.evaluate(async () => {
    // @ts-ignore - Clerk SDK는 window에 globals 주입
    const clerk = window?.Clerk;
    if (!clerk?.session) return null;
    return await clerk.session.getToken();
  });
  if (!token) throw new Error("Clerk 토큰을 가져올 수 없습니다.");

  const headers = { Authorization: `Bearer ${token}` };
  const wsRes = await page.request.get(`${apiUrl}/api/v1/workspaces`, { headers });
  const wsList = await wsRes.json().catch(() => []);

  let wsId: string;
  if (Array.isArray(wsList) && wsList.length > 0) {
    wsId = wsList[0].id;
  } else {
    const createRes = await page.request.post(`${apiUrl}/api/v1/workspaces`, {
      headers: { ...headers, "Content-Type": "application/json" },
      data: { name: "E2E 테스트 워크스페이스" },
    });
    wsId = (await createRes.json()).id;
  }

  // ── localStorage에 activeWorkspaceId 주입 (Zustand persist 형식) ──
  await page.evaluate((id) => {
    localStorage.setItem(
      "kairos-workspace",
      JSON.stringify({ state: { activeWorkspaceId: id }, version: 0 }),
    );
  }, wsId);

  await page.context().storageState({ path: AUTH_FILE });
});
