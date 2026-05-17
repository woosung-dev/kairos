// Multi-Agent QA 자격증명 추출 — 5계정 자동 로그인 후 clerk_user_id + JWT 추출 (Sprint 18 → 19)
/**
 * Sprint 18 → 19 Multi-Agent QA 자격증명 추출 spec.
 *
 * 5계정 (Sentinel A/B, Casual, Mobile, Power) 순차 frontend 자동 로그인 →
 * Clerk session JWT + /api/v1/auth/me 응답에서 user info 추출 →
 * seed-credentials.env 자동 업데이트.
 *
 * 실행 (frontend dev 서버 :3000 + backend :8000 떠 있어야 함):
 *   cd frontend
 *   E2E_BASE_URL=http://localhost:3000 E2E_API_URL=http://localhost:8000 \
 *     pnpm exec playwright test e2e/tests/qa-extract-credentials.spec.ts \
 *     --no-deps --workers=1 --reporter=list
 *
 * 산출:
 *   docs/dev-log/2026-05-17-multi-agent-qa-sprint18/seed-credentials.env
 *   (QA_<PERSONA>_CLERK_USER_ID + JWT + JWT_EXPIRES_AT 5개 채워짐)
 *
 * 주의:
 *   - 한 번 실행에 5계정 순차 로그인 → ~1-2분 소요
 *   - Clerk dev session token TTL 60분 → 60분 안에 seed 스크립트 실행 필수
 *   - 재실행 시 기존 JWT 덮어쓰기
 *
 * Plan: ~/.claude/plans/wise-hugging-newell.md
 */
import { test, expect } from "@playwright/test";
import * as fs from "node:fs";
import * as path from "node:path";

// 보안: PASSWORD 는 절대 코드에 하드코딩 금지. 실행 시 ENV로 주입.
// 사용 예: QA_PASSWORD=xxx pnpm exec playwright test ...
const PASSWORD = process.env.QA_PASSWORD ?? "";
if (!PASSWORD) {
  throw new Error(
    "QA_PASSWORD 환경변수가 설정되지 않았습니다. ~/.kairos-qa-secrets/seed-credentials-*.env 의 QA_*_PASSWORD 값을 사용하세요.",
  );
}
const PERSONAS = [
  { key: "SENTINEL_A", email: "wkddntjd3429@naver.com" },
  { key: "SENTINEL_B", email: "wkddntjd3429-0@naver.com" },
  { key: "CASUAL", email: "wkddntjd3429-1@naver.com" },
  { key: "MOBILE", email: "wkddntjd3429-3@naver.com" },
  { key: "POWER", email: "wkddntjd3429-5@naver.com" },
] as const;

const ENV_PATH = path.resolve(
  __dirname,
  "../../../docs/dev-log/2026-05-17-multi-agent-qa-sprint18/seed-credentials.env",
);
const API_URL = process.env.E2E_API_URL ?? "http://localhost:8000";
// JWT template name (Clerk dashboard > JWT Templates 에서 생성, TTL 3600+ 권장).
// 환경변수 미설정 시 default(60초) — 즉시 만료되어 sub-agent 불가.
const JWT_TEMPLATE = process.env.QA_JWT_TEMPLATE ?? "qa-1h";

// auth.setup 의 storageState 의존성 우회 — 매 페르소나마다 fresh context.
test.use({ storageState: { cookies: [], origins: [] } });

interface PersonaCredential {
  user_id: string;
  clerk_id: string;
  jwt: string;
  expires_at: string;
}

test.describe.serial("QA credentials extraction (Sprint 18 → 19)", () => {
  test("extract 5 personas clerk_user_id + JWT", async ({ browser }) => {
    test.setTimeout(300_000); // 5 min for 5 sequential logins

    const results: Record<string, PersonaCredential> = {};

    for (const persona of PERSONAS) {
      console.log(`\n[${persona.key}] 로그인 시작: ${persona.email}`);
      const context = await browser.newContext({
        // CORS 우회 — local FE → local BE 호출 안전
      });
      const page = await context.newPage();

      try {
        await page.goto("/sign-in");
        await page.locator('input[name="identifier"]').fill(persona.email);
        await page.getByRole("button", { name: /continue|계속/i }).click();
        await page.locator('input[type="password"]').fill(PASSWORD);
        await page.getByRole("button", { name: /continue|sign in|로그인|계속/i }).click();
        // dashboard 또는 redirect URL 도달까지 대기
        await page.waitForURL(/\/dashboard|\/$/, { timeout: 30_000 });

        // Clerk session JWT 추출 — JWT template 으로 long-TTL 발급 (default 60초 회피)
        const token: string | null = await page.evaluate(async (templateName: string) => {
          // @ts-expect-error Clerk SDK 가 window 에 global 주입
          const clerk = window?.Clerk;
          if (!clerk?.session) return null;
          try {
            return await clerk.session.getToken({ template: templateName });
          } catch (err) {
            // template 미존재 시 default token (60초) fallback — 즉시 만료 위험 알림
            console.warn(`[clerk] template '${templateName}' 미존재, default 60초 token 사용. err=${err}`);
            return await clerk.session.getToken();
          }
        }, JWT_TEMPLATE);
        if (!token) throw new Error(`${persona.key} JWT 추출 실패 — Clerk session 없음`);

        // /api/v1/users/me 호출로 user_id + clerk_id 추출 (auth router prefix=/users)
        const meRes = await page.request.get(`${API_URL}/api/v1/users/me`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!meRes.ok()) {
          const body = await meRes.text();
          throw new Error(
            `${persona.key} /api/v1/users/me 실패 status=${meRes.status()} body[0..200]=${body.slice(0, 200)}`,
          );
        }
        const me = (await meRes.json()) as Record<string, string>;

        // JWT exp claim 디코딩 (base64url payload)
        const payloadB64 = token.split(".")[1];
        const payload = JSON.parse(
          Buffer.from(payloadB64.replace(/-/g, "+").replace(/_/g, "/"), "base64").toString(),
        ) as { sub: string; exp: number };

        const expiresAt = new Date(payload.exp * 1000).toISOString();
        const clerkId = me.clerkId ?? me.clerk_id ?? payload.sub ?? "";
        const userId = me.id ?? "";

        if (!clerkId || !userId) {
          throw new Error(
            `${persona.key} user info 누락 — /auth/me 응답: ${JSON.stringify(me)}`,
          );
        }

        results[persona.key] = {
          user_id: userId,
          clerk_id: clerkId,
          jwt: token,
          expires_at: expiresAt,
        };
        console.log(
          `  ✅ ${persona.key}: user_id=${userId} clerk_id=${clerkId} expires=${expiresAt}`,
        );
      } finally {
        await context.close();
      }
    }

    // seed-credentials.env 자동 업데이트
    let envContent = fs.readFileSync(ENV_PATH, "utf-8");
    for (const [key, val] of Object.entries(results)) {
      envContent = envContent.replace(
        new RegExp(`(QA_${key}_CLERK_USER_ID=).*`),
        `$1${val.clerk_id}`,
      );
      envContent = envContent.replace(
        new RegExp(`(QA_${key}_JWT=).*`),
        `$1${val.jwt}`,
      );
      envContent = envContent.replace(
        new RegExp(`(QA_${key}_JWT_EXPIRES_AT=).*`),
        `$1${val.expires_at}`,
      );
    }
    fs.writeFileSync(ENV_PATH, envContent);
    console.log(`\n📝 seed-credentials.env 업데이트 완료: ${ENV_PATH}`);

    expect(Object.keys(results)).toHaveLength(5);
  });
});
