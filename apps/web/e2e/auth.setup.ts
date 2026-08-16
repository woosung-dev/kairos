import { test as setup } from "@playwright/test";
import path from "node:path";

import { ensureAccount, login } from "./team-helpers";

/**
 * 로그인 + 워크스페이스 보장 setup (ADR-031 — Better Auth).
 * 저장된 storageState (cookies + localStorage)를 이후 테스트들이 재사용.
 *
 * 동작:
 *   1) /sign-in 폼에 email/password 로그인 (Google OAuth 는 자동화 대상 아님)
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

/** Better Auth jwt 플러그인이 발급하는 JWT. 세션 쿠키가 있어야 200 이다. */
async function getAuthToken(page: import("@playwright/test").Page): Promise<string> {
  // 페이지 origin 기준 절대 URL — baseURL 상속에 의존하지 않는다 (team-helpers 와 동일 이유).
  const res = await page.request.get(new URL("/api/auth/token", page.url()).toString());
  if (!res.ok()) {
    throw new Error(`GET /api/auth/token → ${res.status()} (세션 쿠키 확인 필요)`);
  }
  const { token } = (await res.json()) as { token?: string };
  if (!token) throw new Error("토큰 응답에 token 필드가 없습니다.");
  return token;
}

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

  // ── 계정 보장 + 로그인 ──
  // CI 는 매 실행 새 DB 를 띄우므로 계정 생성이 선행돼야 한다 (ADR-031).
  // 로그인은 폼 경로를 그대로 관통한다 — data-testid 가 e2e 계약이다.
  await page.goto("/sign-in");
  await ensureAccount(page, email, password, "E2E 사용자");
  await login(page, email, password);

  // ── 워크스페이스 보장 (API 직접 호출) ──
  // 토큰은 Better Auth jwt 플러그인의 엔드포인트에서 받는다 (window 전역 의존 없음).
  const token = await getAuthToken(page);

  const headers = { Authorization: `Bearer ${token}` };
  // BL-027 fix: GET/POST 응답 .ok() 가드 + 명시 throw.
  // 기존 .json().catch(() => []) silent fallback은 503/HTML 응답을 빈 배열로 위장 →
  // 후속 POST에서 다시 .json() 호출 시 SyntaxError 도미노 (Unexpected token '<').
  // E2E_API_URL stale 또는 Cloud Run service down 회귀를 1번의 fail에서 즉시 식별.
  const wsRes = await page.request.get(`${apiUrl}/api/v1/workspaces`, { headers });
  if (!wsRes.ok()) {
    const body = await wsRes.text();
    throw new Error(
      `[e2e auth.setup] GET /api/v1/workspaces 실패 — status=${wsRes.status()} ` +
        `apiUrl=${apiUrl} body[0..200]=${body.slice(0, 200)}\n` +
        `→ E2E_API_URL secret 또는 백엔드 기동 상태 점검 필요 (BL-027).`,
    );
  }
  const wsList = await wsRes.json();

  let wsId: string;
  if (Array.isArray(wsList) && wsList.length > 0) {
    wsId = wsList[0].id;
  } else {
    const createRes = await page.request.post(`${apiUrl}/api/v1/workspaces`, {
      headers: { ...headers, "Content-Type": "application/json" },
      data: { name: "E2E 테스트 워크스페이스" },
    });
    if (!createRes.ok()) {
      const body = await createRes.text();
      throw new Error(
        `[e2e auth.setup] POST /api/v1/workspaces 실패 — status=${createRes.status()} ` +
          `apiUrl=${apiUrl} body[0..200]=${body.slice(0, 200)}\n` +
          `→ E2E_API_URL secret 또는 백엔드 기동 상태 점검 필요 (BL-027).`,
      );
    }
    const created = await createRes.json();
    wsId = created.id;
  }

  // ── localStorage에 activeWorkspaceId 주입 (Zustand persist 형식) ──
  await page.evaluate((id) => {
    localStorage.setItem(
      "kairos-workspace",
      // version 은 store.ts 의 persist version 과 일치해야 한다 — 낮으면 migrate 가
      // 값을 버려서 주입이 무효화된다 (ADR-031 로 0 → 1).
      JSON.stringify({ state: { activeWorkspaceId: id }, version: 1 }),
    );
  }, wsId);

  await page.context().storageState({ path: AUTH_FILE });
});
