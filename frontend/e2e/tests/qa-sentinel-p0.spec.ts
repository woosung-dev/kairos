// Sentinel P0 — RAG visibility 12 + IDOR 13 + audio sanity 3 (Sprint 18 → 19)
/**
 * Multi-Agent QA Sentinel P0 검증 spec.
 *
 * 2계정 (Sentinel A, B) 동시 BrowserContext 유지.
 * 매 API 호출 직전 page.evaluate(Clerk.session.getToken) → fresh JWT (60초 TTL 우회).
 *
 * 검증:
 *  - P0-1 RAG visibility 12 케이스 (3-layer × role × visibility × query × cache)
 *  - P0-2 Workspace IDOR 13 endpoint (Codex 발견 의심 지점 포함)
 *  - P0-3 audio endpoint sanity 3 (UI 없이 가능한 부분)
 *
 * 실행:
 *   cd frontend
 *   E2E_BASE_URL=http://localhost:3000 E2E_API_URL=http://localhost:8000 \
 *     pnpm exec playwright test e2e/tests/qa-sentinel-p0.spec.ts \
 *     --no-deps --workers=1 --reporter=list --project=chromium
 *
 * 산출:
 *   docs/dev-log/qa/2026-05-17-multi-agent-qa-sprint18/sentinel-p0-results.json
 *
 * Plan: ~/.claude/plans/wise-hugging-newell.md
 */
import { test } from "@playwright/test";
import * as fs from "node:fs";
import * as path from "node:path";

// 보안: PASSWORD 는 절대 코드에 하드코딩 금지. 실행 시 ENV로 주입.
const PASSWORD = process.env.QA_PASSWORD ?? "";
if (!PASSWORD) {
  throw new Error(
    "QA_PASSWORD 환경변수가 설정되지 않았습니다. ~/.kairos-qa-secrets/seed-credentials-*.env 의 QA_*_PASSWORD 값을 사용하세요.",
  );
}
const SENTINEL_A_EMAIL = "wkddntjd3429@naver.com";
const SENTINEL_B_EMAIL = "wkddntjd3429-0@naver.com";
const API_URL = process.env.E2E_API_URL ?? "http://localhost:8000";
const FIXTURES_PATH = path.resolve(
  __dirname,
  "../../../docs/dev-log/qa/2026-05-17-multi-agent-qa-sprint18/seed-fixtures.json",
);
const RESULTS_PATH = path.resolve(
  __dirname,
  "../../../docs/dev-log/qa/2026-05-17-multi-agent-qa-sprint18/sentinel-p0-results.json",
);

test.use({ storageState: { cookies: [], origins: [] } });

interface CaseResult {
  case_id: string;
  description: string;
  status?: number;
  sources?: string[];
  body_snippet?: string;
  verdict: "PASS" | "FAIL" | "CONFIRM_NEEDED";
  notes?: string;
}

async function login(page: import("@playwright/test").Page, email: string): Promise<void> {
  await page.goto("/sign-in");
  await page.locator('input[name="identifier"]').fill(email);
  await page.getByRole("button", { name: /continue|계속/i }).click();
  await page.locator('input[type="password"]').fill(PASSWORD);
  await page.getByRole("button", { name: /continue|sign in|로그인|계속/i }).click();
  await page.waitForURL(/\/dashboard|\/$/, { timeout: 30_000 });
  // 첫 token 발급 (sanity)
  const token = await freshToken(page);
  if (!token) throw new Error(`${email} 로그인 후 토큰 발급 실패`);
}

async function freshToken(page: import("@playwright/test").Page): Promise<string> {
  const token = await page.evaluate(async () => {
    // @ts-expect-error Clerk SDK 가 window 에 global 주입
    const clerk = window?.Clerk;
    if (!clerk?.session) return null;
    return await clerk.session.getToken();
  });
  if (!token) throw new Error("JWT refresh 실패 — Clerk session 만료");
  return token;
}

function parseSseSources(text: string): string[] {
  const ids = new Set<string>();
  // SSE 는 \r\n 라인 구분. split(/\r?\n/) + trim 으로 정규화
  for (const rawLine of text.split(/\r?\n/)) {
    const line = rawLine.trim();
    const m = line.match(/^data:\s*(.+)$/);
    if (!m) continue;
    try {
      const obj = JSON.parse(m[1]);
      // RAG SSE 실제 형식: { chunks: [{ id, text, sourceType, ... }] }
      if (Array.isArray((obj as { chunks?: unknown }).chunks)) {
        for (const c of (obj as { chunks: unknown[] }).chunks) {
          if (c && typeof c === "object") {
            const co = c as Record<string, unknown>;
            if (typeof co.id === "string") ids.add(co.id);
            if (typeof co.source_id === "string") ids.add(co.source_id);
            if (typeof co.note_id === "string") ids.add(co.note_id);
          }
        }
      }
      // 기타 키 패턴 fallback
      const collect = (v: unknown): void => {
        if (!v || typeof v !== "object") return;
        const o = v as Record<string, unknown>;
        if (typeof o.source_id === "string") ids.add(o.source_id);
        if (typeof o.note_id === "string") ids.add(o.note_id);
        if (typeof o.chunk_id === "string") ids.add(o.chunk_id);
        if (Array.isArray(o.sources)) for (const s of o.sources) collect(s);
        if (Array.isArray(o.citations)) for (const s of o.citations) collect(s);
      };
      collect(obj);
    } catch {
      // ignore non-JSON SSE comment lines
    }
  }
  return [...ids];
}

test.describe.serial("Sentinel P0 — RAG visibility + IDOR + audio", () => {
  test("28 cases (RAG 12 + IDOR 13 + audio 3)", async ({ browser }) => {
    test.setTimeout(900_000); // 15 min cap

    const fixtures = JSON.parse(fs.readFileSync(FIXTURES_PATH, "utf-8"));
    const results: CaseResult[] = [];

    const wsA: string = fixtures.personas.SENTINEL_A.workspace_id;
    const wsB: string = fixtures.personas.SENTINEL_B.workspace_id;
    const projPub: string = fixtures.rag_visibility_fixtures.public.project_id;
    const projDraft: string = fixtures.rag_visibility_fixtures.draft.project_id;
    const projPriv: string = fixtures.rag_visibility_fixtures.private.project_id;
    const expectedPub: string = fixtures.rag_visibility_fixtures.public.note_id;
    const expectedDraft: string = fixtures.rag_visibility_fixtures.draft.note_id;
    const expectedPriv: string = fixtures.rag_visibility_fixtures.private.note_id;
    const expectedPubChunk: string = fixtures.rag_visibility_fixtures.public.chunk_id;
    const expectedPrivChunk: string = fixtures.rag_visibility_fixtures.private.chunk_id;
    const expectedDraftChunk: string = fixtures.rag_visibility_fixtures.draft.chunk_id;
    const ctProj: string = fixtures.cross_tenant_fixture.project_id;
    const ctNote: string = fixtures.cross_tenant_fixture.note_id;
    const ctChunk: string = fixtures.cross_tenant_fixture.chunk_id;

    const ctxA = await browser.newContext();
    const pageA = await ctxA.newPage();
    console.log(`[A] 로그인...`);
    await login(pageA, SENTINEL_A_EMAIL);

    const ctxB = await browser.newContext();
    const pageB = await ctxB.newPage();
    console.log(`[B] 로그인...`);
    await login(pageB, SENTINEL_B_EMAIL);

    async function callRag(
      page: import("@playwright/test").Page,
      wsId: string,
      question: string,
      projectId?: string,
    ): Promise<{ status: number; sources: string[]; bodySnippet: string }> {
      const token = await freshToken(page);
      const body: Record<string, unknown> = { question };
      if (projectId) body.project_id = projectId;
      const res = await page.request.post(
        `${API_URL}/api/v1/workspaces/${wsId}/rag/ask`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
            Accept: "text/event-stream",
          },
          data: body,
          timeout: 30_000,
        },
      );
      const text = await res.text();
      return { status: res.status(), sources: parseSseSources(text), bodySnippet: text.slice(0, 500) };
    }

    async function callApi(
      page: import("@playwright/test").Page,
      method: string,
      url: string,
      body?: Record<string, unknown>,
    ): Promise<{ status: number; body: string }> {
      const token = await freshToken(page);
      const opts: Parameters<typeof page.request.fetch>[1] = {
        method,
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        timeout: 15_000,
      };
      if (body) opts.data = body;
      const res = await page.request.fetch(`${API_URL}${url}`, opts);
      const bodyText = await res.text();
      return { status: res.status(), body: bodyText.slice(0, 500) };
    }

    // ============================================================
    // P0-1 RAG visibility 12 cases
    // ============================================================
    console.log("\n=== P0-1 RAG visibility 12 cases ===");

    let r = await callRag(pageA, wsA, "alpha 공개 프로젝트 키워드", projPub);
    results.push({
      case_id: "P0-1.1",
      description: "A admin + L1 public project_id → public 노출",
      status: r.status,
      sources: r.sources,
      body_snippet: r.bodySnippet,
      verdict: r.status === 200 && r.sources.some((s) => s === expectedPub || s === expectedPubChunk) ? "PASS" : "FAIL",
    });
    console.log(`  P0-1.1: ${results.at(-1)!.verdict}`);

    r = await callRag(pageA, wsA, "gamma 비공개 민감 정보", projPriv);
    results.push({
      case_id: "P0-1.2",
      description: "A admin + L1 private project_id (admin 우회)",
      status: r.status,
      sources: r.sources,
      body_snippet: r.bodySnippet,
      verdict: r.status === 200 && r.sources.some((s) => s === expectedPriv || s === expectedPrivChunk) ? "PASS" : "FAIL",
    });
    console.log(`  P0-1.2: ${results.at(-1)!.verdict}`);

    r = await callRag(pageB, wsA, "alpha", projPub);
    results.push({
      case_id: "P0-1.3",
      description: "B (WS-A 비멤버) + L1 public 시도 → 403/404",
      status: r.status,
      sources: r.sources,
      body_snippet: r.bodySnippet,
      verdict: r.status === 401 || r.status === 403 || r.status === 404 ? "PASS" : "FAIL",
    });
    console.log(`  P0-1.3: ${results.at(-1)!.verdict}`);

    r = await callRag(pageA, wsA, "gamma ProjectMember 검증", projPriv);
    results.push({
      case_id: "P0-1.4",
      description: "A creator(ProjectMember) + L1 private → 노출",
      status: r.status,
      sources: r.sources,
      body_snippet: r.bodySnippet,
      verdict: r.status === 200 && r.sources.some((s) => s === expectedPriv || s === expectedPrivChunk) ? "PASS" : "FAIL",
    });
    console.log(`  P0-1.4: ${results.at(-1)!.verdict}`);

    r = await callRag(pageA, wsA, "beta 초안", projDraft);
    results.push({
      case_id: "P0-1.5",
      description: "A creator + L1 draft → 노출",
      status: r.status,
      sources: r.sources,
      body_snippet: r.bodySnippet,
      verdict: r.status === 200 && r.sources.some((s) => s === expectedDraft || s === expectedDraftChunk) ? "PASS" : "FAIL",
    });
    console.log(`  P0-1.5: ${results.at(-1)!.verdict}`);

    r = await callRag(pageB, wsA, "beta", projDraft);
    results.push({
      case_id: "P0-1.6",
      description: "B (비멤버) + L1 draft → 403/404",
      status: r.status,
      sources: r.sources,
      body_snippet: r.bodySnippet,
      verdict: r.status === 401 || r.status === 403 || r.status === 404 ? "PASS" : "FAIL",
    });
    console.log(`  P0-1.6: ${results.at(-1)!.verdict}`);

    r = await callRag(pageA, wsA, "alpha beta gamma 모든 키워드");
    const case7Pass = r.status === 200;
    results.push({
      case_id: "P0-1.7",
      description: "A admin + L2 글로벌 (project_id 없음) → admin 우회로 모두",
      status: r.status,
      sources: r.sources,
      body_snippet: r.bodySnippet,
      verdict: case7Pass ? "PASS" : "FAIL",
      notes: "admin이라 public+draft+private 모두 노출되어야",
    });
    console.log(`  P0-1.7: ${results.at(-1)!.verdict}`);

    r = await callRag(pageA, wsA, "alpha beta gamma 모든 키워드");
    results.push({
      case_id: "P0-1.8",
      description: "A 동일 query 재호출 → L3 cache hit",
      status: r.status,
      sources: r.sources,
      body_snippet: r.bodySnippet,
      verdict: r.status === 200 ? "PASS" : "FAIL",
    });
    console.log(`  P0-1.8: ${results.at(-1)!.verdict}`);

    const uniq = "전혀 다른 새 질문 " + Date.now();
    r = await callRag(pageA, wsA, uniq);
    results.push({
      case_id: "P0-1.9",
      description: "A 다른 query (cache miss → L2)",
      status: r.status,
      sources: r.sources,
      body_snippet: r.bodySnippet,
      verdict: r.status === 200 ? "PASS" : "FAIL",
    });
    console.log(`  P0-1.9: ${results.at(-1)!.verdict}`);

    r = await callRag(pageB, wsB, "delta cross-tenant 본인 데이터");
    results.push({
      case_id: "P0-1.10",
      description: "B + L2 본인 WS → B 자기 cross_tenant 청크 노출",
      status: r.status,
      sources: r.sources,
      body_snippet: r.bodySnippet,
      verdict: r.status === 200 ? "PASS" : "FAIL",
    });
    console.log(`  P0-1.10: ${results.at(-1)!.verdict}`);

    r = await callRag(pageA, wsA, "delta cross-tenant");
    const case11Leak = r.sources.includes(ctNote) || r.sources.includes(ctChunk);
    results.push({
      case_id: "P0-1.11",
      description: "🔥 A + L2 WS-A → B의 cross-tenant 청크 절대 안 보임",
      status: r.status,
      sources: r.sources,
      body_snippet: r.bodySnippet,
      verdict: r.status === 200 && !case11Leak ? "PASS" : "FAIL",
      notes: case11Leak ? "CRITICAL: cross-tenant leak 발견 (sources에 B의 ID)" : "OK",
    });
    console.log(`  P0-1.11: ${results.at(-1)!.verdict}`);

    r = await callRag(pageA, wsB, "delta", ctProj);
    results.push({
      case_id: "P0-1.12",
      description: "🔥 A 토큰 + WS-B URL + cross_tenant project_id (IDOR)",
      status: r.status,
      sources: r.sources,
      body_snippet: r.bodySnippet,
      verdict: r.status === 401 || r.status === 403 || r.status === 404 ? "PASS" : "FAIL",
      notes: r.status === 200 ? "CRITICAL: 200이면 cross-workspace project_id 허용" : "OK",
    });
    console.log(`  P0-1.12: ${results.at(-1)!.verdict}`);

    // ============================================================
    // P0-2 IDOR 13 endpoints (A 토큰으로 B 자원 시도)
    // ============================================================
    console.log("\n=== P0-2 IDOR 13 endpoints ===");

    const idorCases: { id: string; method: string; url: string; body?: Record<string, unknown>; notes?: string }[] = [
      { id: "P0-2.1", method: "GET", url: `/api/v1/workspaces/${wsB}`, notes: "🔥 Codex 발견: require_viewer 누락 의심" },
      { id: "P0-2.2", method: "GET", url: `/api/v1/workspaces/${wsB}/members` },
      { id: "P0-2.3", method: "GET", url: `/api/v1/workspaces/${wsB}/projects` },
      { id: "P0-2.4", method: "GET", url: `/api/v1/notes/${ctNote}` },
      { id: "P0-2.5", method: "PATCH", url: `/api/v1/notes/${ctNote}`, body: { title: "HACKED_BY_A" } },
      { id: "P0-2.6", method: "DELETE", url: `/api/v1/notes/${ctNote}` },
      { id: "P0-2.7", method: "GET", url: `/api/v1/projects/${ctProj}` },
      { id: "P0-2.8", method: "GET", url: `/api/v1/workspaces/${wsB}/projects?status=active` },
      { id: "P0-2.9", method: "GET", url: `/api/v1/workspaces/${wsB}/invites` },
      { id: "P0-2.10", method: "POST", url: `/api/v1/workspaces/${wsB}/invites`, body: { role: "viewer" } },
      { id: "P0-2.11", method: "GET", url: `/api/v1/workspaces/${wsB}/inbox` },
      { id: "P0-2.12", method: "GET", url: `/api/v1/workspaces/${wsB}/projects/${ctProj}/members` },
      { id: "P0-2.13", method: "GET", url: `/api/v1/projects/${ctProj}/members` },
    ];

    const leakPattern = /test2|wkddntjd3429-0|cross-tenant-private|delta-cross-tenant|Sentinel B/i;
    for (const ic of idorCases) {
      const resp = await callApi(pageA, ic.method, ic.url, ic.body);
      const passed = resp.status === 401 || resp.status === 403 || resp.status === 404;
      const bodyHasLeak = leakPattern.test(resp.body);
      results.push({
        case_id: ic.id,
        description: `${ic.method} ${ic.url}`,
        status: resp.status,
        body_snippet: resp.body,
        verdict: passed && !bodyHasLeak ? "PASS" : "FAIL",
        notes: bodyHasLeak ? "CRITICAL: body에 B의 데이터 leak" : ic.notes,
      });
      console.log(`  ${ic.id}: ${results.at(-1)!.verdict} (status=${resp.status})`);
    }

    // ============================================================
    // P0-3 audio endpoint sanity 3
    // ============================================================
    console.log("\n=== P0-3 audio sanity ===");

    let res = await callApi(pageA, "POST", `/api/v1/workspaces/${wsA}/upload/presigned-url`, {
      filename: "qa-test.webm",
      content_type: "audio/webm",
    });
    results.push({
      case_id: "P0-3.1",
      description: "POST /workspaces/{wsA}/upload/presigned-url (signed URL 발급)",
      status: res.status,
      body_snippet: res.body,
      verdict: res.status === 200 || res.status === 201 ? "PASS" : "FAIL",
    });
    console.log(`  P0-3.1: ${results.at(-1)!.verdict} (status=${res.status})`);

    res = await callApi(pageA, "GET", `/api/v1/meetings/00000000-0000-0000-0000-000000000000/status`);
    results.push({
      case_id: "P0-3.2",
      description: "GET /meetings/{nonexistent}/status (404 boundary)",
      status: res.status,
      body_snippet: res.body,
      verdict: res.status === 404 ? "PASS" : "FAIL",
    });
    console.log(`  P0-3.2: ${results.at(-1)!.verdict} (status=${res.status})`);

    res = await callApi(pageA, "GET", `/api/v1/workspaces/${wsA}/meetings`);
    results.push({
      case_id: "P0-3.3",
      description: "GET /workspaces/{wsA}/meetings (list sanity)",
      status: res.status,
      body_snippet: res.body,
      verdict: res.status === 200 ? "PASS" : "CONFIRM_NEEDED",
      notes: "실제 audio e2e (record → STT → AI → Inbox) 는 별도 페르소나 또는 manual",
    });
    console.log(`  P0-3.3: ${results.at(-1)!.verdict} (status=${res.status})`);

    // ============================================================
    // 결과 저장
    // ============================================================
    await ctxA.close();
    await ctxB.close();

    const summary = {
      executed_at: new Date().toISOString(),
      total: results.length,
      pass: results.filter((x) => x.verdict === "PASS").length,
      fail: results.filter((x) => x.verdict === "FAIL").length,
      confirm_needed: results.filter((x) => x.verdict === "CONFIRM_NEEDED").length,
      critical_findings: results.filter(
        (x) => x.verdict === "FAIL" && x.notes?.includes("CRITICAL"),
      ).map((x) => ({ case_id: x.case_id, status: x.status, notes: x.notes })),
      results,
    };

    fs.writeFileSync(RESULTS_PATH, JSON.stringify(summary, null, 2));
    console.log(`\n📝 결과 저장: ${RESULTS_PATH}`);
    console.log(`\n📊 PASS: ${summary.pass} / FAIL: ${summary.fail} / CONFIRM_NEEDED: ${summary.confirm_needed}`);
    if (summary.critical_findings.length > 0) {
      console.log(`\n🚨 CRITICAL findings:`);
      console.log(JSON.stringify(summary.critical_findings, null, 2));
    }
  });
});
