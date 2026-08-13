// 멀티계정 팀 spine e2e 회귀: 공용 인증/시드/SSE 헬퍼 (owner+member 2계정, 실 RBAC 관통, mock 금지)
import type { Page, APIResponse } from "@playwright/test";

export const API_URL = process.env.E2E_API_URL ?? "http://localhost:8000";

const LOCAL_HOSTS = new Set(["localhost", "127.0.0.1", "::1", "0.0.0.0"]);

/**
 * 팀 시드는 워크스페이스·초대·프로젝트·노트를 **실제로 생성**한다. `E2E_API_URL` 이 로컬이 아니면
 * 그 대상 DB 가 오염되므로 기본적으로 거부한다 (BL-DX-E2E-API-URL-1).
 *
 * 배경: `frontend/.env.local` 의 `E2E_API_URL` 이 프로덕션 Cloud Run 을 가리키는 동안
 * `NEXT_PUBLIC_API_URL` 은 localhost 였다. override 없이 team-setup 을 돌리면 프로덕션에
 * 시드가 들어간다. CI 는 `LOCAL_API_URL`(localhost)을 주입하므로 이 가드에 걸리지 않는다.
 *
 * 원격 대상 시드가 의도된 경우에만 `E2E_ALLOW_REMOTE_SEED=1` 로 명시 허용한다.
 */
export function assertLocalSeedTarget(apiUrl: string = API_URL): void {
  if (process.env.E2E_ALLOW_REMOTE_SEED === "1") return;
  const host = new URL(apiUrl).hostname;
  if (LOCAL_HOSTS.has(host)) return;
  throw new Error(
    `[team seed 차단] E2E_API_URL 이 로컬이 아니다: ${apiUrl}\n` +
      `이 시드는 워크스페이스·초대·프로젝트·노트를 실제로 생성하므로 대상 DB 를 오염시킨다.\n` +
      `로컬 백엔드로 돌리려면 E2E_API_URL=http://localhost:8001 을 명시하라.\n` +
      `원격 대상이 의도한 것이면 E2E_ALLOW_REMOTE_SEED=1 을 함께 지정하라.`,
  );
}

// 결정적 팀 시드 — 고정 식별자로 discover-or-create (멱등, 누적 방지)
export const TEAM_WS_NAME = "E2E Team Workspace";
export const RAG_PUBLIC_TITLE = "[E2E] RAG public";
export const RAG_PRIVATE_TITLE = "[E2E] RAG private";
export const RAG_DRAFT_TITLE = "[E2E] draft only";

// RAG 누수 검증용 유니크 토큰 — 각 노트 plain_text 선두에 심어 chunk.text(200자 truncate) 안에 포함되게 함.
export const TOKEN_PUBLIC = "CYAN42";
export const TOKEN_PRIVATE = "MAGENTA99";
export const PUBLIC_NOTE_TEXT = `${TOKEN_PUBLIC} 공개 프로젝트 검색 키워드. 이 노트는 팀 전체에 보입니다.`;
export const PRIVATE_NOTE_TEXT = `${TOKEN_PRIVATE} 비공개 프로젝트 기밀 내용. 멤버는 접근 불가해야 합니다.`;

export type ApiMethod = "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
export type WorkspaceRole = "owner" | "admin" | "member" | "viewer";

// Clerk SDK 는 window 에 globals 주입 — any 금지용 로컬 shim.
interface ClerkWindow {
  Clerk?: { session?: { getToken: () => Promise<string | null> } };
}

/** Clerk dev 로그인 (locale-proof: input[name="identifier"], BL-021). */
export async function clerkLogin(
  page: Page,
  email: string,
  password: string,
): Promise<void> {
  await page.goto("/sign-in");
  await page.locator('input[name="identifier"]').fill(email);
  await page.getByRole("button", { name: /continue|계속/i }).click();
  await page.locator('input[type="password"]').fill(password);
  await page.getByRole("button", { name: /continue|sign in|로그인|계속/i }).click();
  await page.waitForURL(/\/dashboard/, { timeout: 30_000 });
}

export interface MeInfo {
  id: string;
  clerkId: string | null;
  email: string | null;
  displayName: string | null;
}

/** 현재 인증 사용자 (GET /users/me). id = User.id = WorkspaceMember.userId — email 빈 lazy-seed 계정도 안전 매칭. */
export async function getMe(page: Page): Promise<MeInfo> {
  const res = await api(page, "GET", "/api/v1/users/me");
  if (!res.ok()) throw new Error(`GET /users/me → ${res.status()}`);
  return (await res.json()) as MeInfo;
}

/** 매 호출 fresh JWT (60s 만료 — hoist 금지). Clerk SDK 비동기 hydrate 대기 후 발급. */
export async function getToken(page: Page): Promise<string> {
  // storageState 로 연 페이지는 Clerk SDK 가 비동기 초기화 — session 준비까지 대기.
  await page
    .waitForFunction(
      () => {
        const w = window as unknown as ClerkWindow;
        return !!w.Clerk?.session;
      },
      { timeout: 20_000 },
    )
    .catch(() => {});
  const token = await page.evaluate(async () => {
    const w = window as unknown as ClerkWindow;
    return (await w.Clerk?.session?.getToken()) ?? null;
  });
  if (!token) throw new Error("Clerk JWT 갱신 실패 — 세션 만료(60s). 즉시 재요청 필요.");
  return token;
}

/** 실 RBAC 관통 인증 요청 (Bearer + JSON, --disable-web-security CORS). 토큰 매번 재발급. */
export async function api(
  page: Page,
  method: ApiMethod,
  path: string,
  body?: unknown,
): Promise<APIResponse> {
  const token = await getToken(page);
  return page.request.fetch(`${API_URL}${path}`, {
    method,
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    ...(body !== undefined ? { data: body } : {}),
    timeout: 20_000,
  });
}

/**
 * console.error + pageerror 수집기. 외부 노이즈(Clerk accounts.dev CSP·favicon·
 * 네트워크 abort·의도적 음성 프로브 4xx/5xx)는 앱 결함이 아니므로 필터.
 * 반환된 getter 로 테스트 종료 시 잔존 에러 단언.
 */
export function collectConsoleErrors(page: Page): () => string[] {
  const errors: string[] = [];
  // 메시지 텍스트 노이즈(앱 console.error/pageerror 용).
  const NOISE_MSG = /accounts\.dev|clerk|content security policy|csp|favicon/i;
  // 브라우저 generic 네트워크 실패 메시지 — URL 미포함이라 텍스트로 구분 불가. 네트워크 실패는
  // response 리스너에서 URL 기반으로 판정하므로 console 레이어에선 제외(Clerk accounts.dev 400 등).
  const NETWORK_MSG = /failed to load resource|net::err|err_aborted|the user aborted|the server responded with a status/i;
  // 외부 서비스 URL(앱 BE 아님) — 구체 도메인만(앱 경로의 부분문자열 오탐 방지: 옛 broad google|sentry 제거).
  const NOISE_URL = /accounts\.dev|\.clerk\.|clerk\.com|sentry\.io|\.ingest\.sentry|google-analytics|googletagmanager|doubleclick|vercel\.live|\/favicon/i;
  page.on("console", (msg) => {
    if (msg.type() !== "error") return;
    const text = msg.text();
    if (NETWORK_MSG.test(text) || NOISE_MSG.test(text)) return;
    errors.push(text);
  });
  page.on("response", (res) => {
    if (res.status() < 400) return;
    const url = res.url();
    if (NOISE_URL.test(url)) return;
    if (res.request().method() === "OPTIONS") return; // CORS 프리플라이트
    errors.push(`HTTP ${res.status()} ${res.request().method()} ${url}`);
  });
  page.on("pageerror", (err) => {
    if (NOISE_MSG.test(err.message)) return;
    errors.push(`pageerror: ${err.message}`);
  });
  return () => errors;
}

/** Tiptap doc 생성 — extract_plain_text(notes/service.py:48) 가 text 노드를 재귀 수집. */
export function buildTiptapDoc(text: string): Record<string, unknown> {
  return {
    type: "doc",
    content: [{ type: "paragraph", content: [{ type: "text", text }] }],
  };
}

/**
 * localStorage.kairos-workspace 에 activeWorkspaceId + ownerUserId(clerkId) 주입.
 * ownerUserId 를 함께 넣어야 panel-layout 의 ensureOwner(clerkId) 가 user 불일치로
 * activeWorkspaceId 를 null 리셋(→ 첫 ws self-heal)하지 않는다 (BL-S27c-12 가드).
 */
export async function injectActiveWorkspace(
  page: Page,
  wsId: string,
  clerkId: string,
): Promise<void> {
  await page.evaluate(
    ({ id, owner }) => {
      localStorage.setItem(
        "kairos-workspace",
        JSON.stringify({ state: { activeWorkspaceId: id, ownerUserId: owner }, version: 0 }),
      );
    },
    { id: wsId, owner: clerkId },
  );
}

// ── RAG SSE 파싱 (결정적 oracle용) ──

export interface SseChunk {
  id: string;
  text: string;
  source: string;
}
export interface SseResult {
  chunks: SseChunk[];
  answer: string;
  sourceCount: number;
  cached: boolean;
}

/**
 * sse-starlette EventSourceResponse 텍스트 파싱.
 * 이벤트: search_results{chunks:[{id,text,source,...}]} · answer{token} · done{sourceCount}.
 * 결정적 oracle = chunk.text 의 유니크 토큰 포함 여부 (answer 텍스트/sourceCount 아님).
 */
export function parseSse(raw: string): SseResult {
  const chunks: SseChunk[] = [];
  let answer = "";
  let sourceCount = 0;
  let cached = false;
  let event = "";
  const dataLines: string[] = [];

  // 한 이벤트 블록(빈 줄 구분) 종료 시 처리. sse-starlette 는 \r\n 라인 + 빈 줄 구분.
  const flush = (): void => {
    const ev = event;
    const dataStr = dataLines.join("");
    event = "";
    dataLines.length = 0;
    if (!dataStr) return;
    let data: unknown;
    try {
      data = JSON.parse(dataStr);
    } catch {
      return;
    }
    if (typeof data !== "object" || data === null) return;
    const obj = data as Record<string, unknown>;
    if (ev === "search_results" && Array.isArray(obj.chunks)) {
      for (const c of obj.chunks) {
        if (c && typeof c === "object") {
          const co = c as Record<string, unknown>;
          chunks.push({
            id: String(co.id ?? ""),
            text: String(co.text ?? ""),
            source: String(co.source ?? ""),
          });
        }
      }
    } else if (ev === "answer" && typeof obj.token === "string") {
      answer += obj.token;
    } else if (ev === "done") {
      if (typeof obj.sourceCount === "number") sourceCount = obj.sourceCount;
      if (obj.cached === true) cached = true;
    }
  };

  for (const rawLine of raw.split(/\r?\n/)) {
    const line = rawLine.replace(/\s+$/, "");
    if (line === "") {
      flush();
      continue;
    }
    if (line.startsWith(":")) continue; // SSE 주석(keep-alive ping)
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
  }
  flush();
  return { chunks, answer, sourceCount, cached };
}

/**
 * 실 RAG ask SSE 호출 (mock 금지). question 에 nonce 부착으로 시맨틱 캐시 회피 옵션.
 * 캐시 함정(embeddings/repository.py:331-391): 캐시 키 = ws+question(role 무관),
 * admin hit 시 visibility 재검증 bypass → member 캐시 public-only 가 admin 결과 오염.
 * T5(member)는 BL-041 가드로 안전, T8(admin)은 T5와 다른 question 사용으로 교차 hit 회피.
 */
export async function ragAsk(
  page: Page,
  workspaceId: string,
  payload: { question: string; projectId?: string | null; timeRange?: string },
): Promise<SseResult> {
  const token = await getToken(page);
  // timeRange 지정 시 BE 가 시맨틱 캐시 skip(rag/service.py:67-73) → 매 호출 fresh
  // vector search → visibility 필터를 실제로 관통(캐시 poisoning·hollow-green 차단).
  // "1m" = 최근 1개월 → 당일 시드 노트 포함.
  const res = await page.request.fetch(
    `${API_URL}/api/v1/workspaces/${workspaceId}/rag/ask`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      },
      data: {
        question: payload.question,
        projectId: payload.projectId ?? null,
        timeRange: payload.timeRange ?? "1m",
      },
      timeout: 60_000,
    },
  );
  if (!res.ok()) {
    throw new Error(
      `rag/ask 실패 status=${res.status()} body=${(await res.text()).slice(0, 200)}`,
    );
  }
  return parseSse(await res.text());
}
