// T14: member 프로젝트 목록 UI — public 카드만 렌더, draft·private 카드 DOM 부재(toHaveCount 0), console.error 0
import { test, expect } from "../../fixtures/team";
import { collectConsoleErrors } from "../../team-helpers";

test.describe("T14 member 프로젝트 목록 public-only", () => {
  test("member /projects: public 카드 보임, draft·private 부재", async ({
    memberPage,
    ragFixtures,
    ensureMemberBaseline,
  }) => {
    await ensureMemberBaseline();
    const errors = collectConsoleErrors(memberPage);
    await memberPage.goto("/projects");

    // public 카드 렌더 (로드 대기)
    await expect(
      memberPage.getByTestId(`project-card-${ragFixtures.publicProjectId}`),
      "public 프로젝트 카드 보임",
    ).toBeVisible();

    // draft·private 카드는 DOM 부재 (visibility 필터 — mutation 시 렌더 → RED)
    await expect(
      memberPage.getByTestId(`project-card-${ragFixtures.draftProjectId}`),
      "draft 카드 DOM 부재",
    ).toHaveCount(0);
    await expect(
      memberPage.getByTestId(`project-card-${ragFixtures.privateProjectId}`),
      "private 카드 DOM 부재",
    ).toHaveCount(0);

    expect(errors(), "console.error 0").toEqual([]);
  });
});
