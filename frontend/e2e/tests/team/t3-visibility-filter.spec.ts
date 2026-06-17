// T3: visibility 필터 — member 는 public 만, draft·private 는 목록 부재 + 상세 404 (작성자 owner)
import { test, expect } from "../../fixtures/team";

interface ProjectList {
  items: Array<{ id: string }>;
}

test.describe("T3 visibility 필터 (member)", () => {
  test("member 목록 public 만 + draft·private 부재 + 상세 404", async ({
    memberPage,
    api,
    teamWsId,
    ragFixtures,
    ensureMemberBaseline,
  }) => {
    await ensureMemberBaseline();

    const list = (await (
      await api(memberPage, "GET", `/api/v1/workspaces/${teamWsId}/projects?pageSize=100`)
    ).json()) as ProjectList;
    const ids = list.items.map((p) => p.id);

    expect(ids, "public 프로젝트는 보임").toContain(ragFixtures.publicProjectId);
    expect(ids, "draft(타인 작성)은 목록 부재").not.toContain(ragFixtures.draftProjectId);
    expect(ids, "private(비멤버)은 목록 부재").not.toContain(ragFixtures.privateProjectId);

    // 상세 직접 접근도 404 (열거 회피 불가)
    const draft = await api(memberPage, "GET", `/api/v1/workspaces/${teamWsId}/projects/${ragFixtures.draftProjectId}`);
    expect(draft.status(), "draft 상세 404").toBe(404);
    const priv = await api(memberPage, "GET", `/api/v1/workspaces/${teamWsId}/projects/${ragFixtures.privateProjectId}`);
    expect(priv.status(), "private 상세 404").toBe(404);
  });
});
