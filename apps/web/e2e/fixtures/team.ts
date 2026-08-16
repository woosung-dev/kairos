// 멀티계정 팀 spine 픽스처: owner/member 이중 컨텍스트 + 실 RBAC 헬퍼 (setRole/warmRbac/ensureMemberBaseline/sseAsk)
import { test as base, expect, type Page, type BrowserContext } from "@playwright/test";
import path from "node:path";
import fs from "node:fs";
import {
  api as apiHelper,
  getToken as getTokenHelper,
  ragAsk,
  type ApiMethod,
  type SseResult,
} from "../team-helpers";

const AUTH_DIR = path.join(__dirname, "..", ".auth");
const OWNER_FILE = path.join(AUTH_DIR, "owner.json");
const MEMBER_FILE = path.join(AUTH_DIR, "member.json");
const FIXTURES_FILE = path.join(AUTH_DIR, "team-fixtures.json");

export type SettableRole = "admin" | "member" | "viewer";

interface RagFixtures {
  publicProjectId: string;
  privateProjectId: string;
  draftProjectId: string;
}
interface TeamMeta {
  teamWsId: string;
  ownerPersonalWsId: string;
  memberRecordId: string;
  memberUserId: string;
  ownerUserId: string;
  memberEmail: string;
  ownerEmail: string;
  ownerPersonalProjectId: string;
  ragFixtures: RagFixtures;
}
interface MemberRow {
  id: string;
  userId: string;
  email: string | null;
  role: string;
}

function readMeta(): TeamMeta {
  if (!fs.existsSync(FIXTURES_FILE)) {
    throw new Error(
      `team-fixtures.json 부재 (${FIXTURES_FILE}) — team-setup 가 먼저 실행돼야 함 (--no-deps 금지).`,
    );
  }
  return JSON.parse(fs.readFileSync(FIXTURES_FILE, "utf-8")) as TeamMeta;
}

async function members(page: Page, wid: string): Promise<MemberRow[]> {
  const res = await apiHelper(page, "GET", `/api/v1/workspaces/${wid}/members`);
  if (!res.ok()) throw new Error(`GET members → ${res.status()}`);
  return (await res.json()) as MemberRow[];
}

export interface TeamFixtures {
  ownerContext: BrowserContext;
  memberContext: BrowserContext;
  ownerPage: Page;
  memberPage: Page;
  meta: TeamMeta;
  teamWsId: string;
  ownerPersonalWsId: string;
  ownerPersonalProjectId: string;
  ragFixtures: RagFixtures;
  /** 실 RBAC 관통 인증 요청 (토큰 매번 재발급). */
  api: (page: Page, method: ApiMethod, p: string, body?: unknown) => Promise<import("@playwright/test").APIResponse>;
  getToken: (page: Page) => Promise<string>;
  /** member 의 현재 WorkspaceMember.id (email 매칭, remove/재초대로 변하므로 동적 해소). null=멤버 아님. */
  getMemberId: () => Promise<string | null>;
  /** owner 의 현재 WorkspaceMember.id. */
  getOwnerMemberId: () => Promise<string>;
  /** owner 가 member role 변경 (sleep·토큰 재발급 없음 — invalidate_member_cache 동기). */
  setRole: (role: SettableRole) => Promise<void>;
  /** member 가 RBAC 보호 endpoint 1회 호출 → _MEMBER_CACHE warm (T6/T8 mutation 관측 전제). */
  warmRbac: (page: Page) => Promise<void>;
  /** member 가 team ws 멤버(role=member)임을 보장 — 제거됐으면 재초대+수락 (membership-mutating spec self-restore). */
  ensureMemberBaseline: () => Promise<void>;
  /** 실 RAG ask SSE. timeRange(기본 "1m") 로 시맨틱 캐시 skip → 매 호출 fresh 검색. */
  sseAsk: (
    page: Page,
    opts: { question: string; projectId?: string | null; timeRange?: string },
  ) => Promise<SseResult>;
}

export const test = base.extend<TeamFixtures>({
  meta: async ({}, use) => {
    await use(readMeta());
  },
  teamWsId: async ({ meta }, use) => {
    await use(meta.teamWsId);
  },
  ownerPersonalWsId: async ({ meta }, use) => {
    await use(meta.ownerPersonalWsId);
  },
  ownerPersonalProjectId: async ({ meta }, use) => {
    await use(meta.ownerPersonalProjectId);
  },
  ragFixtures: async ({ meta }, use) => {
    await use(meta.ragFixtures);
  },

  ownerContext: async ({ browser }, use) => {
    const ctx = await browser.newContext({ storageState: OWNER_FILE });
    await use(ctx);
    await ctx.close();
  },
  memberContext: async ({ browser }, use) => {
    const ctx = await browser.newContext({ storageState: MEMBER_FILE });
    await use(ctx);
    await ctx.close();
  },
  ownerPage: async ({ ownerContext }, use) => {
    const p = await ownerContext.newPage();
    await p.goto("/dashboard"); // 앱 컨텍스트 확보 (토큰은 /api/auth/token 이 준다)
    await use(p);
  },
  memberPage: async ({ memberContext }, use) => {
    const p = await memberContext.newPage();
    await p.goto("/dashboard");
    await use(p);
  },

  api: async ({}, use) => {
    await use(apiHelper);
  },
  getToken: async ({}, use) => {
    await use(getTokenHelper);
  },

  getMemberId: async ({ ownerPage, meta }, use) => {
    await use(async () => {
      const rows = await members(ownerPage, meta.teamWsId);
      const row = rows.find((m) => m.userId === meta.memberUserId);
      return row?.id ?? null;
    });
  },
  getOwnerMemberId: async ({ ownerPage, meta }, use) => {
    await use(async () => {
      const rows = await members(ownerPage, meta.teamWsId);
      const row = rows.find((m) => m.userId === meta.ownerUserId);
      if (!row) throw new Error("owner member row 부재");
      return row.id;
    });
  },

  setRole: async ({ ownerPage, meta, getMemberId }, use) => {
    await use(async (role) => {
      const id = await getMemberId();
      if (!id) throw new Error("setRole: member 가 team ws 멤버가 아님 — ensureMemberBaseline 먼저");
      const res = await apiHelper(ownerPage, "PATCH", `/api/v1/workspaces/${meta.teamWsId}/members/${id}`, {
        role,
      });
      if (!res.ok()) {
        throw new Error(`setRole(${role}) → ${res.status()}: ${(await res.text()).slice(0, 200)}`);
      }
      // sleep / 토큰 재발급 없음: invalidate_member_cache 동기(invite_service.py:253).
    });
  },

  warmRbac: async ({ meta }, use) => {
    await use(async (page) => {
      const res = await apiHelper(page, "GET", `/api/v1/workspaces/${meta.teamWsId}/projects`);
      // 200 기대 (멤버면). RoleChecker 통과 = _MEMBER_CACHE 적재.
      if (!res.ok()) throw new Error(`warmRbac → ${res.status()} (member 상태 확인)`);
    });
  },

  ensureMemberBaseline: async ({ ownerPage, memberPage, meta, getMemberId, setRole }, use) => {
    await use(async () => {
      let id = await getMemberId();
      if (!id) {
        // 재초대 + 수락 (이전 destructive 테스트가 제거한 경우).
        const inv = await apiHelper(ownerPage, "POST", `/api/v1/workspaces/${meta.teamWsId}/invites`, {
          role: "member",
          maxUses: null,
          expiresInDays: 30,
        });
        if (!inv.ok()) throw new Error(`재초대 발급 → ${inv.status()}`);
        const code = ((await inv.json()) as { code: string }).code;
        const acc = await apiHelper(memberPage, "POST", `/api/v1/invites/${code}/accept`);
        if (![200, 201, 409].includes(acc.status())) {
          throw new Error(`재수락 → ${acc.status()}`);
        }
        id = await getMemberId();
        if (!id) throw new Error("ensureMemberBaseline: 재초대 후에도 멤버 아님");
      }
      await setRole("member");
    });
  },

  sseAsk: async ({ meta }, use) => {
    await use(async (page, opts) => ragAsk(page, meta.teamWsId, opts));
  },
});

export { expect };
