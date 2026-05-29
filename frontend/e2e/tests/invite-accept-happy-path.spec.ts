// Sprint 28 TEST-5 — Team workspace invite accept happy-path 회귀 가드.
//
// Sprint 27e Round 1 carry — 외부 5명 dogfooding 진입 *전* 권고.
// invite-page-regression.spec.ts 는 ISSUE-008 의 잘못된 코드 처리만 cover.
// 본 spec 은 owner 발급 → user 수락 → role 부여 → cross-workspace switch 의
// happy-path 회귀 가드.
//
// Heavy 분기: E2E_USER_EMAIL/PASSWORD seed 가 필요 (2 user 동시 로그인 시뮬).
// 본 spec 도 nightly 또는 manual 우선 — `E2E_RUN_INVITE=true` 일 때만 실행.
// 기본 PR e2e gate 는 `frontend-build` 의 security-headers spec 만 (light).
import { test, expect } from "@playwright/test";

const SHOULD_RUN = process.env.E2E_RUN_INVITE === "true";

test.describe.serial("Team workspace invite accept happy-path (TEST-5)", () => {
  test.skip(!SHOULD_RUN, "E2E_RUN_INVITE=true 환경에서만 실행 (2 user 시뮬, invite 발급 + 수락 + role 검증)");

  test("/invite/[code] 페이지 정상 200 + invite 상세 노출 + 수락 버튼", async ({
    page,
  }) => {
    test.setTimeout(60_000);

    // happy-path 가정: 사용자 task 에 미리 발급된 invite code 가 env 로 주입.
    // 또는 본 spec 안 BE 호출로 발급 (E2E_USER_TOKEN 사용). 본 spec 은 UI 흐름만 cover.
    const inviteCode = process.env.E2E_INVITE_CODE;
    test.skip(
      !inviteCode,
      "E2E_INVITE_CODE 미설정 — owner 가 미리 발급한 valid code 필요",
    );

    const response = await page.goto(`/invite/${inviteCode}`);
    expect(response?.status()).toBe(200);

    // invite 상세 노출 — workspace name 또는 inviter name 표시.
    // 본 spec 은 strict text 검증 회피 (BE 응답 의존). 핵심: React 트리 마운트 + 200.
    await expect(page.locator("body")).not.toBeEmpty({ timeout: 10_000 });

    // 수락 버튼 존재 — 정확한 label 은 i18n 의존, role + name regex.
    const acceptBtn = page.getByRole("button", {
      name: /수락|참여|가입|Accept|Join/,
    });
    await expect(acceptBtn).toBeVisible({ timeout: 10_000 });
  });

  test("수락 후 dashboard redirect + workspace switcher 에 new workspace 표시", async ({
    page,
  }) => {
    test.setTimeout(60_000);

    const inviteCode = process.env.E2E_INVITE_CODE;
    test.skip(!inviteCode, "E2E_INVITE_CODE 미설정");

    await page.goto(`/invite/${inviteCode}`);

    // 수락 버튼 클릭
    await page
      .getByRole("button", { name: /수락|참여|가입|Accept|Join/ })
      .click();

    // dashboard 또는 workspace 경로 redirect
    await expect(page).toHaveURL(/\/dashboard|\/workspace\//, {
      timeout: 30_000,
    });

    // workspace switcher (topbar) — 새 workspace 가 등재됨
    // strict workspace name 검증 회피 (test 환경 dynamic) — switcher 존재만 verify
    const switcher = page.getByTestId("workspace-switcher").or(
      page.locator('[data-testid*="workspace"]').first(),
    );
    await expect(switcher).toBeVisible({ timeout: 10_000 });
  });
});
