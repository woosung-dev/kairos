// T22: 노트 삭제 정책 — 작성자 본인 + admin 이상만 (BL-NOTE-DELETE-POLICY-1)
//
// 권한은 화면에서 버튼이 안 보이는 것으로 증명되지 않는다. 본 신호는 **API 직격 시 거부되는가** 이고
// 버튼 부재는 그 위의 UX 층이다. 두 층을 모두 덮는다.
//
// ⚠ 나온스 노트(CYAN42 / MAGENTA99)는 다른 스펙의 관측 기반이므로 건드리지 않는다.
//    이 스펙은 자기가 만든 임시 노트만 쓰고 끝나면 되돌린다.
import { test, expect } from "../../fixtures/team";
import { buildTiptapDoc, collectConsoleErrors, getMe, injectActiveWorkspace } from "../../team-helpers";
import type { Page } from "@playwright/test";

const TEMP_PREFIX = "[E2E] t22 임시";

async function createNote(
  api: (page: Page, method: "POST" | "DELETE", path: string, body?: unknown) => Promise<{ status(): number; json(): Promise<unknown> }>,
  page: Page,
  wsId: string,
  label: string,
): Promise<string> {
  const res = await api(page, "POST", `/api/v1/workspaces/${wsId}/notes`, {
    title: `${TEMP_PREFIX} ${label} ${Date.now()}`,
    content: buildTiptapDoc(`${TEMP_PREFIX} ${label} 본문`),
  });
  expect(res.status(), "임시 노트 생성 201").toBe(201);
  return ((await res.json()) as { id: string }).id;
}

test.describe.serial("T22 노트 삭제 정책 (작성자 본인 + admin 이상)", () => {
  test.afterEach(async ({ ensureMemberBaseline }) => {
    await ensureMemberBaseline();
  });

  test("API — member 는 남의 노트를 삭제할 수 없다 (403), 읽기는 200", async ({
    ownerPage,
    memberPage,
    api,
    teamWsId,
    ensureMemberBaseline,
  }) => {
    await ensureMemberBaseline();

    // 관측 전 계정 신원 확인 — owner/member 가 실제로 서로 다른 사용자인지
    const ownerMe = await getMe(ownerPage);
    const memberMe = await getMe(memberPage);
    expect(memberMe.id, "member 와 owner 는 다른 사용자여야 한다").not.toBe(ownerMe.id);

    const noteId = await createNote(api, ownerPage, teamWsId, "owner-note");
    try {
      const read = await api(memberPage, "GET", `/api/v1/workspaces/${teamWsId}/notes/${noteId}`);
      expect(read.status(), "member 는 그 노트를 읽을 수 있다 → 200").toBe(200);

      const del = await api(memberPage, "DELETE", `/api/v1/workspaces/${teamWsId}/notes/${noteId}`);
      expect(del.status(), "비-작성자 member 삭제 → 403 (404 아님: 이미 읽을 수 있는 노트)").toBe(403);

      const after = await api(memberPage, "GET", `/api/v1/workspaces/${teamWsId}/notes/${noteId}`);
      expect(after.status(), "거부는 곧 보존 — 노트가 남아 있어야 한다").toBe(200);
    } finally {
      await api(ownerPage, "DELETE", `/api/v1/workspaces/${teamWsId}/notes/${noteId}`);
    }
  });

  test("API — member 는 자기가 쓴 노트를 삭제할 수 있다 (204)", async ({
    memberPage,
    api,
    teamWsId,
    ensureMemberBaseline,
  }) => {
    await ensureMemberBaseline();
    const noteId = await createNote(api, memberPage, teamWsId, "member-note");

    const del = await api(memberPage, "DELETE", `/api/v1/workspaces/${teamWsId}/notes/${noteId}`);
    expect(del.status(), "작성자 본인 삭제 → 204").toBe(204);

    const after = await api(memberPage, "GET", `/api/v1/workspaces/${teamWsId}/notes/${noteId}`);
    expect(after.status(), "삭제 후 조회 → 404").toBe(404);
  });

  test("API — admin 은 남의 노트를 삭제할 수 있다 (204)", async ({
    ownerPage,
    memberPage,
    api,
    teamWsId,
    setRole,
    ensureMemberBaseline,
  }) => {
    await ensureMemberBaseline();
    const noteId = await createNote(api, ownerPage, teamWsId, "owner-note-for-admin");

    await setRole("admin");
    const del = await api(memberPage, "DELETE", `/api/v1/workspaces/${teamWsId}/notes/${noteId}`);
    expect(del.status(), "admin 은 남의 노트도 삭제 가능 → 204").toBe(204);
  });

  test("브라우저 — member 는 남의 노트에서 삭제 버튼을 못 보고, 편집 버튼은 본다", async ({
    ownerPage,
    memberPage,
    api,
    teamWsId,
    ensureMemberBaseline,
  }) => {
    await ensureMemberBaseline();
    const memberMe = await getMe(memberPage);
    const noteId = await createNote(api, ownerPage, teamWsId, "owner-note-ui");

    const errors = collectConsoleErrors(memberPage);
    try {
      await memberPage.goto("/");
      await injectActiveWorkspace(memberPage, teamWsId, memberMe.clerkId ?? "");
      await memberPage.goto(`/notes/${noteId}`);

      // 셀렉터는 태그를 가정하지 않는다 (aria-label 단독)
      await expect(
        memberPage.getByLabel("편집"),
        "정책은 삭제에만 적용된다 — 편집은 그대로 보여야 한다",
      ).toBeVisible();
      await expect(
        memberPage.getByLabel("삭제"),
        "비-작성자 member 에게 삭제 버튼이 보이면 안 된다",
      ).toHaveCount(0);

      expect(errors(), "앱 코드가 던진 console.error / pageerror / 앱 BE 4xx 는 0건").toEqual([]);
    } finally {
      await api(ownerPage, "DELETE", `/api/v1/workspaces/${teamWsId}/notes/${noteId}`);
    }
  });

  test("브라우저 — member 는 자기가 쓴 노트에서 삭제 버튼을 본다", async ({
    memberPage,
    api,
    teamWsId,
    ensureMemberBaseline,
  }) => {
    await ensureMemberBaseline();
    const memberMe = await getMe(memberPage);
    const noteId = await createNote(api, memberPage, teamWsId, "member-note-ui");

    try {
      await memberPage.goto("/");
      await injectActiveWorkspace(memberPage, teamWsId, memberMe.clerkId ?? "");
      await memberPage.goto(`/notes/${noteId}`);

      await expect(
        memberPage.getByLabel("삭제"),
        "작성자 본인에게는 삭제 버튼이 보여야 한다",
      ).toBeVisible();
    } finally {
      await api(memberPage, "DELETE", `/api/v1/workspaces/${teamWsId}/notes/${noteId}`);
    }
  });
});
