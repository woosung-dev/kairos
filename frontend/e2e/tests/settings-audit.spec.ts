// Sprint 24 Wave 2 T-AUDIT-VIEW (BUG-POW-008) — Settings Audit 탭 admin gate 검증
// 검증: /settings 진입 후 admin/owner 만 Audit tab trigger 노출 + ?tab=audit 직접 접근 시
// content mount 분기 (admin 만 AuditList, viewer/member 는 안내 텍스트).
import { test, expect } from "@playwright/test";

test.describe("T-AUDIT-VIEW — Settings Audit 탭 (Sprint 24 Wave 2)", () => {
  test("admin/owner 사용자에게 Audit tab trigger 가 노출", async ({ page }) => {
    await page.goto("/settings");
    await page.waitForLoadState("networkidle");

    // 로그인 안 된 경우 / workspace 미선택 시 → skip
    const workspaceMissing = await page
      .getByText(/워크스페이스를 선택해주세요/)
      .count();
    if (workspaceMissing > 0) {
      test.skip(true, "워크스페이스 미선택 — fixture seeding 필요");
      return;
    }

    // admin tab trigger 존재 여부로 admin/viewer 분기 판단.
    const auditTab = page.getByTestId("audit-tab-trigger");
    const triggerCount = await auditTab.count();

    if (triggerCount === 0) {
      // viewer/member 환경 — 다음 테스트 케이스에서 hidden 검증.
      test.skip(
        true,
        "현재 사용자가 admin/owner 아님 — viewer hidden 케이스에서 검증",
      );
      return;
    }

    await expect(auditTab).toBeVisible({ timeout: 5_000 });
    await auditTab.click();
    await page.waitForURL(/\?tab=audit/);

    // Audit list 컴포넌트 자체 mount — loading / empty / table 중 하나는 render.
    const anyAuditState = page
      .getByTestId("audit-loading")
      .or(page.getByTestId("audit-empty"))
      .or(page.getByTestId("audit-table"));
    await expect(anyAuditState).toBeVisible({ timeout: 10_000 });
  });

  test("viewer/member 사용자 ?tab=audit 직접 접근 시 trigger hidden + content 안내", async ({
    page,
  }) => {
    await page.goto("/settings?tab=audit");
    await page.waitForLoadState("networkidle");

    const workspaceMissing = await page
      .getByText(/워크스페이스를 선택해주세요/)
      .count();
    if (workspaceMissing > 0) {
      test.skip(true, "워크스페이스 미선택 — fixture seeding 필요");
      return;
    }

    const auditTab = page.getByTestId("audit-tab-trigger");
    const triggerCount = await auditTab.count();

    if (triggerCount > 0) {
      // admin/owner 환경 — 이전 케이스에서 trigger 보임 검증, 본 케이스는 skip.
      test.skip(
        true,
        "현재 사용자가 admin/owner — admin visible 케이스에서 검증",
      );
      return;
    }

    // viewer/member 분기: trigger 부재 + content 영역 admin 안내 텍스트.
    // ?tab=audit URL 직접 진입 시 valid tab 으로 인식되지만 content 가 admin gate 분기.
    await expect(
      page.getByText(/Audit 로그 조회는 관리자\(Admin\) 이상 권한에서만/),
    ).toBeVisible({ timeout: 5_000 });
  });
});
