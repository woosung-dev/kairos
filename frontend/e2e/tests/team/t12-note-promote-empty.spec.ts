// T12: 0-chunk(빈 plain_text) note promote → 400 NotePromoteNotEmbeddedError 분기 가드
import { test, expect } from "../../fixtures/team";

test.describe("T12 빈 노트 promote 400 가드", () => {
  test("plain_text 빈 노트 promote → 400", async ({
    ownerPage,
    api,
    teamWsId,
    ownerPersonalWsId,
  }) => {
    // 빈 Tiptap doc → extract_plain_text "" → promote 400 가드.
    const created = await api(ownerPage, "POST", `/api/v1/workspaces/${ownerPersonalWsId}/notes`, {
      title: "empty note",
      content: { type: "doc", content: [] },
    });
    expect(created.status()).toBe(201);
    const noteId = ((await created.json()) as { id: string }).id;

    const promo = await api(
      ownerPage,
      "POST",
      `/api/v1/workspaces/${ownerPersonalWsId}/notes/${noteId}/promote`,
      { targetWorkspaceId: teamWsId },
    );
    expect(promo.status(), "빈 plain_text 노트 promote → 400 (mutation 시 202 silent fail)").toBe(400);
  });
});
