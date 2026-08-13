// 멀티계정 팀 spine e2e 시드: owner+member 2계정 로그인 → 실 invite/accept → RAG 픽스처 → 이중 storageState
import { test as setup, expect } from "@playwright/test";
import path from "node:path";
import fs from "node:fs";
import {
  TEAM_WS_NAME,
  RAG_PUBLIC_TITLE,
  RAG_PRIVATE_TITLE,
  RAG_DRAFT_TITLE,
  TOKEN_PUBLIC,
  TOKEN_PRIVATE,
  PUBLIC_NOTE_TEXT,
  PRIVATE_NOTE_TEXT,
  assertLocalSeedTarget,
  clerkLogin,
  api,
  getMe,
  buildTiptapDoc,
  injectActiveWorkspace,
  type ApiMethod,
} from "./team-helpers";
import type { Page } from "@playwright/test";

const AUTH_DIR = path.join(__dirname, ".auth");
const OWNER_FILE = path.join(AUTH_DIR, "owner.json");
const MEMBER_FILE = path.join(AUTH_DIR, "member.json");
const FIXTURES_FILE = path.join(AUTH_DIR, "team-fixtures.json");

interface Member {
  id: string;
  userId: string;
  email: string | null;
  role: string;
}
interface Project {
  id: string;
  title: string;
  visibility: string;
}

async function jsonOk(page: Page, method: ApiMethod, p: string, body?: unknown): Promise<unknown> {
  const res = await api(page, method, p, body);
  if (!res.ok()) {
    throw new Error(`${method} ${p} → ${res.status()}: ${(await res.text()).slice(0, 200)}`);
  }
  return res.json();
}

/** team ws 의 멤버 목록 (camelCase: id/userId/email/role). */
async function listMembers(page: Page, wid: string): Promise<Member[]> {
  return (await jsonOk(page, "GET", `/api/v1/workspaces/${wid}/members`)) as Member[];
}

/** project 를 고정 title 로 discover-or-create (멱등). visibility 는 create 시 지정. */
async function discoverOrCreateProject(
  page: Page,
  wid: string,
  title: string,
  visibility: "public" | "draft" | "private",
): Promise<string> {
  // 목록은 페이지네이션 dict {items,...} + visibility 필터. owner(role bypass)는 전 visibility 조회.
  const list = (await jsonOk(page, "GET", `/api/v1/workspaces/${wid}/projects?pageSize=100`)) as {
    items: Project[];
  };
  const existing = list.items.find((p) => p.title === title);
  if (existing) return existing.id;
  const created = (await jsonOk(page, "POST", `/api/v1/workspaces/${wid}/projects`, {
    title,
    visibility,
  })) as { id: string };
  return created.id;
}

async function pollEmbedded(page: Page, wid: string, noteId: string): Promise<void> {
  for (let i = 0; i < 40; i++) {
    const st = (await jsonOk(
      page,
      "GET",
      `/api/v1/workspaces/${wid}/notes/${noteId}/embedding-status`,
    )) as { status: string; chunkCount: number };
    if (st.status === "completed" && st.chunkCount >= 1) return;
    if (st.status === "failed") throw new Error(`RAG 시드 임베딩 실패 note=${noteId} (OPENAI 키 확인)`);
    await page.waitForTimeout(1500);
  }
  throw new Error(`RAG 시드 임베딩 timeout note=${noteId} (60s)`);
}

/**
 * 프로젝트에 토큰 노트가 정확히 1개 임베딩돼 있도록 보장 (dedup).
 * 중복 노트는 top-K 검색을 오염시켜 retrieval 비결정성을 만든다 → 정확히 1개로 정리.
 * 노트 임베딩 시 delete_caches 가 호출돼 시맨틱 캐시도 함께 정리됨(notes/pipeline_service.py:102).
 */
async function ensureSingleEmbeddedNote(
  page: Page,
  wid: string,
  projectId: string,
  noteText: string,
  token: string,
): Promise<void> {
  const title = `${token} note`;
  const listed = (await jsonOk(
    page,
    "GET",
    `/api/v1/workspaces/${wid}/notes?projectId=${projectId}&pageSize=100`,
  )) as { items?: Array<{ id: string; title: string }> } | Array<{ id: string; title: string }>;
  const items = Array.isArray(listed) ? listed : (listed.items ?? []);
  const tokenNotes = items.filter((n) => n.title === title);

  // 정확히 1개 + 임베딩 완료면 재사용.
  if (tokenNotes.length === 1) {
    const st = (await jsonOk(
      page,
      "GET",
      `/api/v1/workspaces/${wid}/notes/${tokenNotes[0].id}/embedding-status`,
    )) as { status: string; chunkCount: number };
    if (st.status === "completed" && st.chunkCount >= 1) return;
  }

  // 그 외(0개·중복·미임베딩): 전부 삭제 후 1개 재생성.
  for (const n of tokenNotes) {
    await api(page, "DELETE", `/api/v1/workspaces/${wid}/notes/${n.id}`);
  }
  const created = (await jsonOk(page, "POST", `/api/v1/workspaces/${wid}/notes`, {
    title,
    content: buildTiptapDoc(noteText),
    projectId,
  })) as { id: string };
  await pollEmbedded(page, wid, created.id);
}

setup("team seed", async ({ browser }) => {
  setup.setTimeout(180_000);

  // 네트워크 호출 전 첫 수 — 원격 대상 시드 차단 (BL-DX-E2E-API-URL-1)
  assertLocalSeedTarget();

  const ownerEmail = process.env.QA_LOCAL_OWNER_EMAIL;
  const ownerPw = process.env.QA_LOCAL_OWNER_PASSWORD;
  const memberEmail = process.env.QA_LOCAL_MEMBER_EMAIL;
  const memberPw = process.env.QA_LOCAL_MEMBER_PASSWORD;
  if (!ownerEmail || !ownerPw || !memberEmail || !memberPw) {
    throw new Error(
      "QA_LOCAL_OWNER_EMAIL/PASSWORD · QA_LOCAL_MEMBER_EMAIL/PASSWORD 가 필요합니다 (.env.local).",
    );
  }

  fs.mkdirSync(AUTH_DIR, { recursive: true });

  // ── 1. owner 로그인 (context A) ──
  const ownerCtx = await browser.newContext();
  const ownerPage = await ownerCtx.newPage();
  await clerkLogin(ownerPage, ownerEmail, ownerPw);
  const ownerMe = await getMe(ownerPage);

  // ── 2. team ws discover-or-create (personal 절대 사용 금지) ──
  const wsList = (await jsonOk(ownerPage, "GET", "/api/v1/workspaces")) as Array<{
    id: string;
    name: string;
    type: string;
  }>;
  const ownerPersonal = wsList.find((w) => w.type === "personal");
  if (!ownerPersonal) throw new Error("owner personal workspace 부재 — 온보딩 상태 확인");
  let team = wsList.find((w) => w.type === "team" && w.name === TEAM_WS_NAME);
  let teamWsId: string;
  if (team) {
    teamWsId = team.id;
  } else {
    const created = (await jsonOk(ownerPage, "POST", "/api/v1/workspaces", {
      name: TEAM_WS_NAME,
    })) as { id: string };
    teamWsId = created.id;
  }

  // ── 3. member 초대 발급 (재사용 우선 — 매 실행 신규 POST 는 활성 초대 무한 누적) ──
  const inviteList = (await jsonOk(
    ownerPage,
    "GET",
    `/api/v1/workspaces/${teamWsId}/invites`,
  )) as Array<{
    code: string;
    role: string;
    isActive: boolean;
    maxUses: number | null;
    expiresAt: string | null;
  }>;
  const reusable = inviteList.find(
    (i) =>
      i.isActive &&
      i.role === "member" &&
      i.maxUses === null &&
      (!i.expiresAt ||
        new Date(i.expiresAt).getTime() - Date.now() > 7 * 86_400_000),
  );
  const invite =
    reusable ??
    ((await jsonOk(ownerPage, "POST", `/api/v1/workspaces/${teamWsId}/invites`, {
      role: "member",
      maxUses: null,
      expiresInDays: 30,
    })) as { code: string });

  // ── 4. member 로그인 (context B) ──
  const memberCtx = await browser.newContext();
  const memberPage = await memberCtx.newPage();
  await clerkLogin(memberPage, memberEmail, memberPw);
  const memberMe = await getMe(memberPage);
  if (memberMe.id === ownerMe.id) {
    throw new Error("owner/member 가 동일 계정으로 로그인됨 — 컨텍스트 격리 실패");
  }

  // ── 5. member 초대 수락 (200/201=가입 · 409=이미 멤버 성공 · 그 외 throw) ──
  const acceptRes = await api(memberPage, "POST", `/api/v1/invites/${invite.code}/accept`);
  if (![200, 201, 409].includes(acceptRes.status())) {
    throw new Error(
      `invite accept 실패 status=${acceptRes.status()}: ${(await acceptRes.text()).slice(0, 200)}`,
    );
  }

  // ── 6. owner 가 member 를 baseline role=member 로 리셋 (userId 매칭 — email 빈 lazy-seed 안전) ──
  let members = await listMembers(ownerPage, teamWsId);
  const memberRec = members.find((m) => m.userId === memberMe.id);
  if (!memberRec) throw new Error(`member(${memberMe.id}) 가 team ws 멤버가 아님 — 시드 실패`);
  if (memberRec.role !== "member") {
    await jsonOk(ownerPage, "PATCH", `/api/v1/workspaces/${teamWsId}/members/${memberRec.id}`, {
      role: "member",
    });
  }

  // ── 7. seed 가드 (hollow-green killer): 정확히 owner+member 2행, userId/role 일치 ──
  members = await listMembers(ownerPage, teamWsId);
  expect(members, "team ws 멤버는 owner+member 2명이어야 함").toHaveLength(2);
  const ownerRow = members.find((m) => m.userId === ownerMe.id);
  const memberRow = members.find((m) => m.userId === memberMe.id);
  expect(ownerRow?.role, "owner 계정은 owner role").toBe("owner");
  expect(memberRow?.role, "member 계정은 member role(baseline)").toBe("member");

  // ── 8. RAG 픽스처 (멱등) ──
  const publicProjectId = await discoverOrCreateProject(ownerPage, teamWsId, RAG_PUBLIC_TITLE, "public");
  const privateProjectId = await discoverOrCreateProject(ownerPage, teamWsId, RAG_PRIVATE_TITLE, "private");
  const draftProjectId = await discoverOrCreateProject(ownerPage, teamWsId, RAG_DRAFT_TITLE, "draft");
  await ensureSingleEmbeddedNote(ownerPage, teamWsId, publicProjectId, PUBLIC_NOTE_TEXT, TOKEN_PUBLIC);
  await ensureSingleEmbeddedNote(ownerPage, teamWsId, privateProjectId, PRIVATE_NOTE_TEXT, TOKEN_PRIVATE);

  // T4(I-9) cross-tenant: owner 개인 ws 의 프로젝트 = team ws prefix 로 접근 시 404 여야 할 "foreign resource".
  const ownerPersonalProjectId = await discoverOrCreateProject(
    ownerPage,
    ownerPersonal.id,
    "[E2E] owner personal project",
    "public",
  );

  // ── 9. localStorage 주입 (양쪽 active ws = team ws + ownerUserId=clerkId) ──
  if (!ownerMe.clerkId || !memberMe.clerkId) {
    throw new Error("clerkId 부재 — ensureOwner 가드 우회 불가");
  }
  await injectActiveWorkspace(ownerPage, teamWsId, ownerMe.clerkId);
  await injectActiveWorkspace(memberPage, teamWsId, memberMe.clerkId);

  // ── 10. storageState 저장 + 픽스처 메타 export ──
  await ownerCtx.storageState({ path: OWNER_FILE });
  await memberCtx.storageState({ path: MEMBER_FILE });
  const fixtures = {
    teamWsId,
    ownerPersonalWsId: ownerPersonal.id,
    memberRecordId: memberRec.id,
    memberUserId: memberMe.id,
    ownerUserId: ownerMe.id,
    memberEmail,
    ownerEmail,
    ownerPersonalProjectId,
    ragFixtures: { publicProjectId, privateProjectId, draftProjectId },
  };
  fs.writeFileSync(FIXTURES_FILE, JSON.stringify(fixtures, null, 2));

  await ownerCtx.close();
  await memberCtx.close();
});
