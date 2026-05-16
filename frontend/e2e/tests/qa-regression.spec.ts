// Sprint 17 QA regression e2e — ISSUE-005 + ISSUE-009 회귀 가드
import { test, expect } from "@playwright/test";

/**
 * Sprint 17 fix 회귀 방지 e2e 모음.
 *
 * 본 spec 은 auth.setup.ts 의 storageState 를 재사용 (인증 상태 + 워크스페이스
 * 보장). 각 시나리오는 단일 fix 의 표면 증상 (콘솔 에러 / HTTP 상태 / UI
 * 텍스트) 만 검증해 시간 비용 최소화.
 */

test.describe("Sprint 17 QA regression 모음", () => {
  test("ISSUE-009: /projects/[id] 렌더링 (useRecentItems hooks order)", async ({
    page,
  }) => {
    test.setTimeout(60_000);

    // 콘솔 에러 수집 — "Rendered more hooks than during the previous render"
    // 가 다시 나타나면 회귀.
    const consoleErrors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") consoleErrors.push(msg.text());
    });

    // local BE 환경 (CI) 에서는 sidebar 가 비어있을 수 있으므로 API 로
    // 직접 project 1개 생성한 뒤 /projects/{id} 진입.
    await page.goto("/dashboard");
    await expect(page.getByRole("heading", { name: "오늘의 Kairos" })).toBeVisible({
      timeout: 15_000,
    });

    // 1. Clerk 토큰 + activeWorkspaceId 확보 (페이지 안에서 fetch)
    const ctx = await page.evaluate(async () => {
      // @ts-ignore — Clerk SDK 가 window 에 주입
      const token = await window.Clerk?.session?.getToken();
      const stored = window.localStorage.getItem("kairos-workspace");
      const parsed = stored ? JSON.parse(stored) : null;
      const wid = parsed?.state?.activeWorkspaceId;
      return { token, wid };
    });
    expect(ctx.token).toBeTruthy();
    expect(ctx.wid).toBeTruthy();

    // 2. project 1개 생성 (API 직접) — 환경 의존성 제거
    const apiUrl = process.env.E2E_API_URL ?? "http://localhost:8000";
    const createRes = await page.request.post(
      `${apiUrl}/api/v1/workspaces/${ctx.wid}/projects`,
      {
        headers: { Authorization: `Bearer ${ctx.token}`, "Content-Type": "application/json" },
        data: { title: "ISSUE-009 e2e", description: "regression test" },
      },
    );
    expect(createRes.ok()).toBeTruthy();
    const project = await createRes.json();
    expect(project.id).toBeTruthy();

    // 3. /projects/{id} 직접 진입 — sidebar 의존 없음
    await page.goto(`/projects/${project.id}`);

    // ErrorBoundary 의 "문제가 발생했습니다" 텍스트 미노출.
    await expect(page.getByText("문제가 발생했습니다")).toHaveCount(0);

    // 페이지 안정 대기 (React Query mount + 첫 fetch)
    await page
      .waitForLoadState("networkidle", { timeout: 15_000 })
      .catch(() => {});

    // 핵심: hooks order 위반 에러 부재.
    const hooksOrderErrors = consoleErrors.filter((m) =>
      /Rendered more hooks than during the previous render/i.test(m),
    );
    expect(hooksOrderErrors).toEqual([]);
  });

  test("ISSUE-005: /notes 페이지에 BE 데이터 반영 (mock 데이터 제거 검증)", async ({
    page,
  }) => {
    test.setTimeout(30_000);

    await page.goto("/notes");
    await expect(page.getByRole("heading", { name: "빠른 메모" })).toBeVisible({
      timeout: 10_000,
    });

    // mock 데이터 흔적 ("Q2 제품 로드맵" / "사용자 리서치") 가 fix 이후 영구 사라져야 함.
    // 이 두 태그는 quick-memo.tsx 가 mock 일 때만 노출 가능. real API 사용 시
    // useProjects 결과 (시작하기/아이디어/회의록) 만 노출 — 본 테스트의 핵심 의도.
    const mockProjectTags = page.locator(
      "text=/Q2 제품 로드맵|사용자 리서치/",
    );
    await expect(mockProjectTags).toHaveCount(0);

    // 참고: "+ 새 메모" 버튼 가시성은 canWrite (workspaceRole 동기화) 에
    // 의존 — CI 에서 race-prone (members API 응답 지연 시 timeout). RBAC 매트릭스는
    // src/features/workspaces/__tests__/store.test.ts (FE) + tests/auth/test_rbac.py (BE)
    // 단위 테스트가 4×4 cell 전수 검증하므로 e2e button 체크 제거.
  });
});
