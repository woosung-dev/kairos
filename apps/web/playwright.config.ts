import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright E2E 설정.
 *
 * - 기본 타겟: 로컬 dev 서버(3003) + 프로덕 BE
 * - CI에서는 재시도 2회, 실패 시 trace 업로드
 * - 세션은 storageState로 재사용해 매 테스트 재로그인 비용 절감
 *
 * 사용법:
 *   pnpm dev -p 3003                    # 다른 터미널
 *   pnpm e2e                             # 전체 실행
 *   pnpm e2e --ui                        # UI 모드로 인터랙티브 디버깅
 *   pnpm e2e tests/home.spec.ts          # 단일 스펙
 */

const PORT = Number(process.env.E2E_PORT ?? 3003);
const BASE_URL = process.env.E2E_BASE_URL ?? `http://localhost:${PORT}`;

// 멀티계정 팀 spine 회귀 스위트 (e2e/tests/team/*) 는 owner+member 2계정 storageState +
// 로컬 BE(:8000) 시드가 필요해 E2E_RUN_TEAM=true 일 때만 활성. 미설정 시 일반 e2e 무영향.
const RUN_TEAM = process.env.E2E_RUN_TEAM === "true";

export default defineConfig({
  testDir: "./e2e",
  // Multi-Agent QA spec (qa-*.spec.ts) 은 로컬 수동 QA 전용 — seed DB / JWT /
  // R2 의존성이 크고 5계정 fixture 필요. CI 게이트 통합 금지.
  testIgnore: process.env.CI ? [/qa-.*\.spec\.ts/] : undefined,
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : "list",

  use: {
    baseURL: BASE_URL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },

  projects: [
    {
      name: "setup",
      testMatch: /auth\.setup\.ts/,
    },
    {
      name: "chromium",
      // r2-1: security-headers.spec.ts 는 public-only project 가 단독 게이트 — chromium 중복 실행 회피.
      // qa-* spec 은 top-level testIgnore 와 동일 — project-level testIgnore 가 top-level 을
      // override 하므로 여기에도 명시 (Playwright 동작).
      testIgnore: [
        /security-headers\.spec\.ts/,
        // 팀 spine 스펙은 gated `team` project(E2E_RUN_TEAM=true) 에서만 실행 —
        // owner/member storageState 가 team-setup 에서만 생성되므로 chromium 에서 제외.
        /tests[\\/]team[\\/]/,
        ...(process.env.CI ? [/qa-.*\.spec\.ts/] : []),
      ],
      use: {
        ...devices["Desktop Chrome"],
        storageState: "e2e/.auth/user.json",
        // E2E는 localhost FE → 프로덕션 BE 호출로 CORS preflight가 차단됨.
        // 프로덕션 backend의 CORS 정책을 건드리지 않기 위해 테스트 환경에서만 web security 비활성화.
        launchOptions: {
          args: ["--disable-web-security"],
        },
      },
      dependencies: ["setup"],
    },
    // Sprint 27e Round 2 BUG-S27e-TEST-r2-1 — public-only project: storageState/setup 의존 없음.
    // FE 보안 헤더 회귀 가드 (security-headers.spec.ts) 의 CI 게이트 운영화 — 로그인 불요.
    // CI chromium 의 ERR_NAME_NOT_RESOLVED (localhost 도 127.0.0.1 도 fail) 회피:
    // --no-sandbox + --host-resolver-rules 로 internal DNS 강제 매핑.
    {
      name: "public-only",
      testMatch: /security-headers\.spec\.ts/,
      use: {
        ...devices["Desktop Chrome"],
        launchOptions: {
          args: [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--host-resolver-rules=MAP localhost 127.0.0.1",
          ],
        },
      },
    },
    // 멀티계정 팀 spine 회귀 (E2E_RUN_TEAM=true). team-setup 이 owner.json/member.json/
    // team-fixtures.json 생성 → team project 가 fixture 로 컨텍스트별 storageState 주입.
    // fullyParallel:false + 실행 시 --workers=1 → 공유 team ws role-mutation race 차단.
    ...(RUN_TEAM
      ? [
          {
            name: "team-setup",
            testMatch: /team\.setup\.ts/,
          },
          {
            name: "team",
            testMatch: /e2e\/tests\/team\/.*\.spec\.ts/,
            fullyParallel: false,
            use: {
              ...devices["Desktop Chrome"],
              // 컨텍스트별 storageState 는 fixture 가 주입 — top-level storageState 없음.
              launchOptions: { args: ["--disable-web-security"] },
            },
            dependencies: ["team-setup"],
          },
        ]
      : []),
  ],

  // CI가 아닌 환경에서만 dev 서버 자동 기동.
  // CI는 별도 step으로 띄워 준비 완료 후 테스트 실행.
  webServer: process.env.CI
    ? undefined
    : {
        command: `pnpm dev -p ${PORT}`,
        url: BASE_URL,
        timeout: 60_000,
        reuseExistingServer: true,
      },
});
