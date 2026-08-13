// T6: revocation 캐시 무효화 — RBAC 캐시 warm 후 owner 가 B 제거 → 같은 테스트서 B 즉시 403 (60s 대기 없이)
import { test, expect } from "../../fixtures/team";

interface WsRow {
  id: string;
}

test.describe.serial("T6 revocation 즉시 반영 (invalidate_member_cache)", () => {
  test.afterEach(async ({ ensureMemberBaseline }) => {
    await ensureMemberBaseline();
  });

  test("제거 직후 B 접근 403 (캐시 즉시 무효화)", async ({
    ownerPage,
    memberPage,
    api,
    teamWsId,
    getMemberId,
    warmRbac,
    ensureMemberBaseline,
  }) => {
    await ensureMemberBaseline();

    // (선행) B 의 RBAC 캐시 warm — 없으면 제거 후 cache-miss DB 조회로 mutation 불가시(hollow-green).
    await warmRbac(memberPage);

    const id = await getMemberId();
    expect(id).not.toBeNull();
    const del = await api(ownerPage, "DELETE", `/api/v1/workspaces/${teamWsId}/members/${id}`);
    expect(del.status()).toBe(204);

    // 같은 테스트 내(60s 대기 없이) 즉시 403 — invalidate_member_cache 호출 검증
    const after = await api(memberPage, "GET", `/api/v1/workspaces/${teamWsId}/projects`);
    expect(after.status(), "제거 직후 즉시 403 (stale 60s 접근 없음)").toBe(403);

    // 실제 제거 확인: B 의 ws 목록에서 team ws 소멸
    const wsList = (await (await api(memberPage, "GET", "/api/v1/workspaces")).json()) as WsRow[];
    expect(wsList.some((w) => w.id === teamWsId), "B 목록에서 team ws 소멸").toBe(false);
  });
});
