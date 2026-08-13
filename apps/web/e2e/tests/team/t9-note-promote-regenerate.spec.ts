// T9: note(생성 직후) promote → regenerate 분기 → BG 재임베딩 completed + 팀 RAG 검색 (QA-0617-A 회귀 가드)
import { test, expect } from "../../fixtures/team";
import { buildTiptapDoc } from "../../team-helpers";

test.describe("T9 note promote regenerate (QA-0617-A)", () => {
  test("생성 직후 promote → regenerate → completed + 팀 RAG 검색", async ({
    ownerPage,
    api,
    teamWsId,
    ownerPersonalWsId,
    sseAsk,
  }) => {
    test.setTimeout(150_000);
    const token = `PROMOTE${Date.now()}`;

    // owner 개인 ws 에 노트 생성 → 임베딩 대기 없이 즉시 promote (source chunk 0 = regenerate 분기).
    const created = await api(ownerPage, "POST", `/api/v1/workspaces/${ownerPersonalWsId}/notes`, {
      title: `${token} note`,
      content: buildTiptapDoc(`${token} 승격 후 재임베딩 검증용 본문 내용입니다.`),
    });
    expect(created.status()).toBe(201);
    const noteId = ((await created.json()) as { id: string }).id;

    const promo = await api(
      ownerPage,
      "POST",
      `/api/v1/workspaces/${ownerPersonalWsId}/notes/${noteId}/promote`,
      { targetWorkspaceId: teamWsId },
    );
    expect(promo.status(), "promote 202 (regenerate 분기)").toBe(202);
    const newNoteId = ((await promo.json()) as { new_note_id: string }).new_note_id;

    // embedding-status 폴링 — fix 시 completed+chunkCount>=1, mutation(session_factory 제거) 시 failed/0.
    let status = "";
    let chunkCount = 0;
    for (let i = 0; i < 40; i++) {
      const st = (await (
        await api(ownerPage, "GET", `/api/v1/workspaces/${teamWsId}/notes/${newNoteId}/embedding-status`)
      ).json()) as { status: string; chunkCount: number };
      status = st.status;
      chunkCount = st.chunkCount;
      if (status === "completed" || status === "failed") break;
      await ownerPage.waitForTimeout(1500);
    }
    expect(status, "regenerate 임베딩 completed (mutation 시 failed)").toBe("completed");
    expect(chunkCount, "복제 chunk >= 1 (mutation 시 0)").toBeGreaterThanOrEqual(1);

    // 팀 RAG 가 승격 노트 내용을 검색 (영구 누락 회귀 방지)
    const rag = await sseAsk(ownerPage, { question: `${token} 본문 내용` });
    expect(
      rag.chunks.some((c) => c.text.includes(token)),
      "승격 노트가 팀 RAG 에서 검색됨",
    ).toBe(true);
  });
});
