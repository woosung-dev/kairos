// T19: 워크스페이스 삭제 — owner 전용 204 / 비멤버·비owner 403 / personal 차단 (I-19)
import { test, expect } from "../../fixtures/team";

test.describe("T19 워크스페이스 삭제 RBAC + personal 차단", () => {
  test("owner 만 삭제 가능, member 403, 삭제 후 목록에서 사라짐", async ({
    ownerPage,
    memberPage,
    api,
  }) => {
    // 일회용 team ws 생성 (owner)
    const createRes = await api(ownerPage, "POST", "/api/v1/workspaces", {
      name: `QA-2607-delete-${Date.now()}`,
    });
    expect(createRes.status(), "일회용 ws 생성 201").toBe(201);
    const ws = await createRes.json();

    // member 는 이 ws 의 멤버가 아님 → 403
    const memberDel = await api(
      memberPage,
      "DELETE",
      `/api/v1/workspaces/${ws.id}`,
    );
    expect(memberDel.status(), "비멤버 삭제 시도 → 403").toBe(403);

    // owner 삭제 → 204
    const ownerDel = await api(
      ownerPage,
      "DELETE",
      `/api/v1/workspaces/${ws.id}`,
    );
    expect(ownerDel.status(), "owner 삭제 → 204").toBe(204);

    // 삭제 후 상세 접근 → 403 (멤버십 자체가 사라짐)
    const getAfter = await api(
      ownerPage,
      "GET",
      `/api/v1/workspaces/${ws.id}`,
    );
    expect(getAfter.status(), "삭제 후 상세 → 403").toBe(403);

    // 목록에서 부재
    const listRes = await api(ownerPage, "GET", "/api/v1/workspaces");
    const list = await listRes.json();
    expect(
      list.some((w: { id: string }) => w.id === ws.id),
      "삭제된 ws 는 목록에서 제외",
    ).toBe(false);
  });

  test("personal ws 삭제 → 403 (PersonalWorkspaceProtected)", async ({
    ownerPage,
    api,
    ownerPersonalWsId,
  }) => {
    const res = await api(
      ownerPage,
      "DELETE",
      `/api/v1/workspaces/${ownerPersonalWsId}`,
    );
    expect(res.status(), "personal 삭제 차단 403").toBe(403);
  });
});
