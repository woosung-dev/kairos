// T8: admin bypass 대칭 + 강등 재격리 — 승격 즉시 private 접근/ RAG MAGENTA, 강등 즉시 재격리 (update invalidate_member_cache)
import { test, expect } from "../../fixtures/team";
import { TOKEN_PRIVATE } from "../../team-helpers";

test.describe.serial("T8 admin bypass + 강등 재격리", () => {
  test.afterEach(async ({ ensureMemberBaseline }) => {
    await ensureMemberBaseline();
  });

  test("승격→admin: private 우회 + RAG MAGENTA / 강등→member: 즉시 재격리", async ({
    memberPage,
    api,
    teamWsId,
    ragFixtures,
    warmRbac,
    setRole,
    sseAsk,
    ensureMemberBaseline,
  }) => {
    test.setTimeout(150_000); // 실 Gemini SSE 2회 + role 전환

    await ensureMemberBaseline();
    await warmRbac(memberPage); // member role 캐시 적재 (mutation 관측 전제)

    // ── 승격 → admin: 즉시 반영 ──
    await setRole("admin");
    const draft = await api(memberPage, "GET", `/api/v1/workspaces/${teamWsId}/projects/${ragFixtures.draftProjectId}`);
    expect(draft.status(), "admin 은 draft 상세 우회 200 (즉시)").toBe(200);
    const priv = await api(memberPage, "GET", `/api/v1/workspaces/${teamWsId}/projects/${ragFixtures.privateProjectId}`);
    expect(priv.status(), "admin 은 private 상세 우회 200 (즉시)").toBe(200);

    const ragAdmin = await sseAsk(memberPage, { question: `${TOKEN_PRIVATE} 비밀 기밀 내용` });
    expect(ragAdmin.cached, "fresh 검색").toBe(false);
    expect(
      ragAdmin.chunks.some((c) => c.text.includes(TOKEN_PRIVATE)),
      "admin RAG 는 private chunk 포함 (role bypass)",
    ).toBe(true);

    // ── 강등 → member: 즉시 재격리 (update invalidate 검증) ──
    await setRole("member");
    const ragMember = await sseAsk(memberPage, { question: `${TOKEN_PRIVATE} 비밀 기밀 내용` });
    expect(
      ragMember.chunks.some((c) => c.text.includes(TOKEN_PRIVATE)),
      "강등 즉시 private chunk 재격리 (60s 대기 없이)",
    ).toBe(false);
  });
});
