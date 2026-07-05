// T21: 프로젝트 삭제 콘텐츠 FK 정책 — 콘텐츠(노트) 있으면 409 차단, 없으면 204 (BL-S27e-5)
import { test, expect } from "../../fixtures/team";

test.describe("T21 프로젝트 삭제 콘텐츠 FK 정책 (BL-S27e-5)", () => {
  test("콘텐츠 없는 프로젝트 → 204 삭제", async ({ ownerPage, teamWsId, api }) => {
    const createRes = await api(
      ownerPage,
      "POST",
      `/api/v1/workspaces/${teamWsId}/projects`,
      { title: `QA-t21-empty-${Date.now()}`, visibility: "public" },
    );
    expect(createRes.status(), "프로젝트 생성 201").toBe(201);
    const project = (await createRes.json()) as { id: string };

    const del = await api(
      ownerPage,
      "DELETE",
      `/api/v1/workspaces/${teamWsId}/projects/${project.id}`,
    );
    expect(del.status(), "콘텐츠 없음 → 204").toBe(204);
  });

  test("노트 연결 프로젝트 → 409 차단, 노트 삭제 후 → 204", async ({
    ownerPage,
    teamWsId,
    api,
  }) => {
    const createRes = await api(
      ownerPage,
      "POST",
      `/api/v1/workspaces/${teamWsId}/projects`,
      { title: `QA-t21-content-${Date.now()}`, visibility: "public" },
    );
    expect(createRes.status(), "프로젝트 생성 201").toBe(201);
    const project = (await createRes.json()) as { id: string };
    let noteId: string | undefined;
    try {
      const noteRes = await api(
        ownerPage,
        "POST",
        `/api/v1/workspaces/${teamWsId}/notes`,
        { title: `QA-t21-note-${Date.now()}`, projectId: project.id },
      );
      expect(noteRes.status(), "노트 생성 201").toBe(201);
      noteId = ((await noteRes.json()) as { id: string }).id;

      // 콘텐츠 있음 → 삭제 차단 409 (+ 상세 안내에 개수)
      const blocked = await api(
        ownerPage,
        "DELETE",
        `/api/v1/workspaces/${teamWsId}/projects/${project.id}`,
      );
      expect(blocked.status(), "콘텐츠 연결 → 409 차단").toBe(409);
      const body = (await blocked.json()) as { detail: string };
      expect(body.detail, "409 상세에 노트 안내 포함").toContain("노트");

      // 노트 삭제 → 콘텐츠 0 → 삭제 성공 204
      const delNote = await api(
        ownerPage,
        "DELETE",
        `/api/v1/workspaces/${teamWsId}/notes/${noteId}`,
      );
      expect(delNote.status(), "노트 삭제 204").toBe(204);
      noteId = undefined;

      const ok = await api(
        ownerPage,
        "DELETE",
        `/api/v1/workspaces/${teamWsId}/projects/${project.id}`,
      );
      expect(ok.status(), "콘텐츠 제거 후 → 204").toBe(204);
    } finally {
      // 실패 경로 정리 — 남은 노트/프로젝트 제거 (성공 시 404, 무해).
      if (noteId) {
        await api(
          ownerPage,
          "DELETE",
          `/api/v1/workspaces/${teamWsId}/notes/${noteId}`,
        );
      }
      await api(
        ownerPage,
        "DELETE",
        `/api/v1/workspaces/${teamWsId}/projects/${project.id}`,
      );
    }
  });
});
