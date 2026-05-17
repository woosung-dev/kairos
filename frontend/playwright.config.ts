import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright E2E 설정.
 *
 * - 기본 타겟: 로컬 dev 서버(3003) + 프로덕 BE
 * - CI에서는 재시도 2회, 실패 시 trace 업로드
 * - Clerk 세션은 storageState로 재사용해 매 테스트 재로그인 비용 절감
 *
 * 사용법:
 *   pnpm dev -p 3003                    # 다른 터미널
 *   pnpm e2e                             # 전체 실행
 *   pnpm e2e --ui                        # UI 모드로 인터랙티브 디버깅
 *   pnpm e2e tests/home.spec.ts          # 단일 스펙
 */

const PORT = Number(process.env.E2E_PORT ?? 3003);
const BASE_URL = process.env.E2E_BASE_URL ?? `http://localhost:${PORT}`;

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
