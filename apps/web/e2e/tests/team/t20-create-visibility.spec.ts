// T20: 프로젝트 생성 다이얼로그 visibility 셀렉터 — 명시 선택 전송 + W-5 시드(미전송 폴백) + private creator 락아웃 회귀
import { test, expect } from "../../fixtures/team";
import type { Page } from "@playwright/test";

interface ProjectRow {
  id: string;
  title: string;
  visibility: string;
}

/** UI 로 프로젝트 생성 — visibility: null=기본값 그대로(미전송), 값 지정 시 Select 조작. */
async function createViaDialog(
  page: Page,
  title: string,
  visibility: "public" | "draft" | "private" | null,
): Promise<void> {
  await page.goto("/projects");
  await page.getByTestId("create-project-button").click();
  await page.getByPlaceholder("예: 신규 기능 기획").fill(title);
  if (visibility) {
    await page.getByTestId("create-project-visibility").click();
    await page.getByTestId(`create-project-visibility-${visibility}`).click();
  }
  if (visibility === "private") {
    await expect(
      page.getByTestId("create-project-private-warning"),
      "private 선택 시 경고 박스 노출",
    ).toBeVisible();
  }
  await page.getByRole("button", { name: "생성", exact: true }).click();
  // 성공 시 다이얼로그 닫힘 (onSuccess → onOpenChange(false))
  await expect(page.getByTestId("create-project-visibility")).toHaveCount(0);
}

async function findByTitle(
  api: (page: Page, method: "GET", p: string) => Promise<import("@playwright/test").APIResponse>,
  page: Page,
  wid: string,
  title: string,
): Promise<ProjectRow | undefined> {
  const res = await api(page, "GET", `/api/v1/workspaces/${wid}/projects?pageSize=100`);
  if (!res.ok()) throw new Error(`GET projects → ${res.status()}`);
  const body = (await res.json()) as { items: ProjectRow[] };
  return body.items.find((p) => p.title === title);
}

test.describe("T20 생성 다이얼로그 visibility", () => {
  test("member 가 private 명시 생성 → 본인 접근 OK (creator 락아웃 회귀 가드)", async ({
    memberPage,
    ownerPage,
    teamWsId,
    api,
    ensureMemberBaseline,
  }) => {
    await ensureMemberBaseline();
    const title = `QA-2607-t20-member-private-${Date.now()}`;
    let projectId: string | undefined;
    try {
      await createViaDialog(memberPage, title, "private");

      const row = await findByTitle(api, memberPage, teamWsId, title);
      expect(row, "member 본인 목록에 private 프로젝트 존재 (락아웃 없음)").toBeTruthy();
      projectId = row!.id;
      expect(row!.visibility).toBe("private");

      const detail = await api(
        memberPage,
        "GET",
        `/api/v1/workspaces/${teamWsId}/projects/${projectId}`,
      );
      expect(detail.status(), "creator 본인 상세 200").toBe(200);
    } finally {
      if (projectId) {
        await api(
          ownerPage,
          "DELETE",
          `/api/v1/workspaces/${teamWsId}/projects/${projectId}`,
        );
      }
    }
  });

  test("owner 가 private 명시 생성 → member 404 + 목록 부재", async ({
    memberPage,
    ownerPage,
    teamWsId,
    api,
    ensureMemberBaseline,
  }) => {
    await ensureMemberBaseline();
    const title = `QA-2607-t20-owner-private-${Date.now()}`;
    let projectId: string | undefined;
    try {
      await createViaDialog(ownerPage, title, "private");

      const ownerRow = await findByTitle(api, ownerPage, teamWsId, title);
      expect(ownerRow, "owner 목록에 존재 (admin bypass)").toBeTruthy();
      projectId = ownerRow!.id;

      const memberRow = await findByTitle(api, memberPage, teamWsId, title);
      expect(memberRow, "member 목록 부재").toBeUndefined();
      const detail = await api(
        memberPage,
        "GET",
        `/api/v1/workspaces/${teamWsId}/projects/${projectId}`,
      );
      expect(detail.status(), "member 상세 404 (존재 은닉)").toBe(404);
    } finally {
      if (projectId) {
        await api(
          ownerPage,
          "DELETE",
          `/api/v1/workspaces/${teamWsId}/projects/${projectId}`,
        );
      }
    }
  });

  test("W-5: draft 시드 초대 수락 후 '워크스페이스 기본값' 생성 → visibility=draft", async ({
    memberPage,
    ownerPage,
    teamWsId,
    api,
    getMemberId,
    ensureMemberBaseline,
  }) => {
    test.setTimeout(90_000); // 멤버 제거→재초대→수락→UI 생성→baseline 복원 (dev 빌드 페이지 로드 포함)
    await ensureMemberBaseline();
    const title = `QA-2607-t20-w5-draft-${Date.now()}`;
    let projectId: string | undefined;
    try {
      // 기존 멤버십 제거 → draft 시드 초대로 재가입 (public 시드는 최종 폴백과 구분 불가)
      const memberId = await getMemberId();
      expect(memberId, "baseline 멤버 존재").toBeTruthy();
      const removed = await api(
        ownerPage,
        "DELETE",
        `/api/v1/workspaces/${teamWsId}/members/${memberId}`,
      );
      expect(removed.status(), "member 제거").toBe(204);

      const inv = await api(ownerPage, "POST", `/api/v1/workspaces/${teamWsId}/invites`, {
        role: "member",
        defaultProjectVisibility: "draft",
        maxUses: null,
        expiresInDays: 1,
      });
      expect(inv.ok(), "draft 시드 초대 발급").toBeTruthy();
      const code = ((await inv.json()) as { code: string }).code;
      const acc = await api(memberPage, "POST", `/api/v1/invites/${code}/accept`);
      expect([200, 201].includes(acc.status()), `재수락 → ${acc.status()}`).toBeTruthy();

      // "워크스페이스 기본값" 그대로 생성 → visibility 미전송 → BE 가 draft 시드 적용
      await createViaDialog(memberPage, title, null);

      const row = await findByTitle(api, memberPage, teamWsId, title);
      expect(row, "creator 는 자기 draft 조회 가능").toBeTruthy();
      projectId = row!.id;
      expect(row!.visibility, "W-5 시드 적용 (draft)").toBe("draft");
    } finally {
      if (projectId) {
        await api(
          ownerPage,
          "DELETE",
          `/api/v1/workspaces/${teamWsId}/projects/${projectId}`,
        );
      }
      // draft 시드 멤버십 정리 → 기본 public 시드 baseline 복원 (후속 스펙 오염 방지)
      const staleId = await getMemberId();
      if (staleId) {
        await api(
          ownerPage,
          "DELETE",
          `/api/v1/workspaces/${teamWsId}/members/${staleId}`,
        );
      }
      await ensureMemberBaseline();
    }
  });
});
