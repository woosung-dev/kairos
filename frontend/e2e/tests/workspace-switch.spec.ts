import { test, expect } from "@playwright/test";

/**
 * Sprint 23 D1 회귀 spec: 워크스페이스 스위처 클릭 → 컨텍스트 즉시 전환
 *
 * 검증 대상 (D1 fix):
 * - WorkspaceSwitcher dropdown 클릭 시 localStorage 의
 *   `kairos-workspace.state.activeWorkspaceId` 가 새 wid 로 갱신
 * - queryClient.invalidateQueries 가 wid-scoped 쿼리만 invalidate
 *   (workspaces.list 보존 → ws list dropdown 계속 표시)
 * - router.refresh() 제거 → invalidateQueries 만으로 사이드바/Today/Inbox 새 데이터
 *
 * 의존: storageState (auth.setup.ts) + 2개 이상 workspace 시드
 * 시드 부재 시 skip (CI 환경 적응).
 */

test.describe("D1 — 워크스페이스 스위처 즉시 전환 (Sprint 23)", () => {
  test("워크스페이스 스위처 클릭 → localStorage activeWorkspaceId 즉시 갱신", async ({
    page,
  }) => {
    await page.goto("/dashboard");
    await page.waitForLoadState("networkidle");

    // 2026-05-29 전체정검 BUG-WS-SWITCH-BROKEN 회귀가드 강화:
    // 이 spec 은 onClick 핸들러 미발화(전환 불능)를 잡아야 하나, 1개 ws 만 시드된
    // 환경에선 non-active 옵션 0개 → 과거 test.skip 으로 무력화(hollow-green)돼
    // 버그가 출시까지 생존했다. 전환 테스트엔 2+ ws 가 필수 전제이므로 부족 시 API 로 시드.
    const token: string | null = await page.evaluate(async () => {
      // @ts-ignore - Clerk SDK globals
      return (await window?.Clerk?.session?.getToken()) ?? null;
    });
    if (token) {
      const apiUrl = process.env.E2E_API_URL ?? "http://localhost:8000";
      const headers = { Authorization: `Bearer ${token}` };
      const listRes = await page.request.get(`${apiUrl}/api/v1/workspaces`, {
        headers,
      });
      if (listRes.ok()) {
        const list = await listRes.json();
        if (Array.isArray(list) && list.length < 2) {
          await page.request.post(`${apiUrl}/api/v1/workspaces`, {
            headers: { ...headers, "Content-Type": "application/json" },
            data: { name: "E2E 전환 테스트 워크스페이스" },
          });
          await page.reload();
          await page.waitForLoadState("networkidle");
        }
      }
    }

    // 현재 wid 확인 (Zustand persist key `kairos-workspace`)
    const wsIdBefore = await page.evaluate(
      () =>
        JSON.parse(localStorage.getItem("kairos-workspace") ?? "{}").state
          ?.activeWorkspaceId,
    );
    if (!wsIdBefore) {
      test.skip(true, "storageState 미주입 — auth setup 의존 carry-over");
      return;
    }

    // WorkspaceSwitcher trigger (aria-label 강제)
    const trigger = page.getByRole("button", { name: /워크스페이스 전환/ });
    await expect(trigger).toBeVisible({ timeout: 10_000 });
    await trigger.click();

    // Sprint 23 Codex 4차 P2-3 fix: active row 검출을 active workspace name 비교로 변경.
    // 이전: svg[class*="text-accent"] — Check 아이콘이 inline style color 사용 → match X.
    // 이후: WorkspaceSwitcher trigger 의 currently selected name 과 menuitem text 비교.
    // 또한 "새 워크스페이스" CTA 항목도 menuitem 이라 명시적 exclude.
    const triggerText = (await trigger.textContent()) ?? "";

    const allMenuItems = await page.getByRole("menuitem").all();
    // 실제 workspace option 만 추출 (create CTA 제외 + active 제외)
    const workspaceOptions: typeof allMenuItems = [];
    for (const item of allMenuItems) {
      const text = (await item.textContent()) ?? "";
      if (text.includes("새 워크스페이스")) continue;
      // active row 는 trigger 의 name 과 동일 prefix 포함 (length 비교 + trim)
      if (
        triggerText.trim().length > 0 &&
        text.trim().startsWith(triggerText.trim().split(/\s+/)[0])
      ) {
        continue;
      }
      workspaceOptions.push(item);
    }

    // 위에서 2+ ws 를 보장했으므로 non-active 옵션은 반드시 존재해야 한다.
    // (과거 hollow-green: 여기서 skip → BUG-WS-SWITCH-BROKEN 미검출.)
    expect(
      workspaceOptions.length,
      "2+ 워크스페이스 보장 후에도 non-active 옵션 0 — 스위처 렌더/시드 회귀",
    ).toBeGreaterThan(0);

    await workspaceOptions[0].click();

    // localStorage activeWorkspaceId 가 새 wid 로 갱신
    await page.waitForFunction(
      (oldWid) => {
        const state = JSON.parse(
          localStorage.getItem("kairos-workspace") ?? "{}",
        ).state;
        return (
          state?.activeWorkspaceId && state.activeWorkspaceId !== oldWid
        );
      },
      wsIdBefore,
      { timeout: 5_000 },
    );

    const wsIdAfter = await page.evaluate(
      () =>
        JSON.parse(localStorage.getItem("kairos-workspace") ?? "{}").state
          ?.activeWorkspaceId,
    );
    expect(wsIdAfter).toBeTruthy();
    expect(wsIdAfter).not.toBe(wsIdBefore);
  });
});
