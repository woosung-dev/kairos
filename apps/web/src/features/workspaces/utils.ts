// 워크스페이스 타입 추론 + BL-035 동일 이름 disambiguation + 전환 무효화 · 알림 딥링크 판정 유틸
import type { Query, QueryClient } from "@tanstack/react-query";
import type { Workspace } from "./types";

const PERSONAL_SEED_SUFFIX = "의 개인 Kairos";

/**
 * BE 응답 우선 사용. 누락 시 Sprint 15 lazy seed 패턴 `{display_name}의 개인 Kairos` 휴리스틱.
 */
export function inferWorkspaceType(
  workspace: Pick<Workspace, "name" | "type">,
): "personal" | "team" {
  if (workspace.type === "personal" || workspace.type === "team") {
    return workspace.type;
  }
  if (workspace.name?.endsWith(PERSONAL_SEED_SUFFIX)) {
    return "personal";
  }
  return "team";
}

/**
 * BL-035: 동일 이름 워크스페이스 disambiguation — created_at 오름차순 #1, #2... 접미사.
 * 단일 이름은 접미사 미부여. type (team/personal) 별로 그룹화 → 두 타입 간 번호 충돌 없음.
 *
 * 반환: Map<workspace.id, "#N">. 그룹 크기 1인 워크스페이스는 Map 미포함 (suffix 없음).
 */
export function buildDisambiguationMap(
  workspaces: Pick<Workspace, "id" | "name" | "type" | "createdAt">[],
): Map<string, string> {
  const suffixMap = new Map<string, string>();
  const groups = new Map<string, typeof workspaces>();
  workspaces.forEach((ws) => {
    const key = `${inferWorkspaceType(ws)}:${ws.name}`;
    const arr = groups.get(key);
    if (arr) arr.push(ws);
    else groups.set(key, [ws]);
  });
  groups.forEach((group) => {
    if (group.length < 2) return;
    const sorted = [...group].sort((a, b) => a.createdAt.localeCompare(b.createdAt));
    sorted.forEach((ws, idx) => {
      suffixMap.set(ws.id, `#${idx + 1}`);
    });
  });
  return suffixMap;
}

/**
 * 워크스페이스 전환 시 무효화 대상 — `["workspaces", "list"]` 만 보존한다 (사용자의 ws 목록 유지).
 * Sprint 23 D1: queryClient.clear() 가 workspaces.list 까지 날려 목록이 잠시 사라지고 race 가 났다.
 * WorkspaceSwitcher 와 알림 딥링크 전환(useWorkspaceDeepLink)이 같이 쓴다 — 복제 금지 (pwa.md §5.5).
 */
export function isWorkspaceScopedQuery(query: Pick<Query, "queryKey">): boolean {
  const key = query.queryKey;
  return !(Array.isArray(key) && key[0] === "workspaces" && key[1] === "list");
}

export function invalidateWorkspaceScopedQueries(queryClient: QueryClient): void {
  void queryClient.invalidateQueries({ predicate: isWorkspaceScopedQuery });
}

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export type WorkspaceDeepLinkDecision =
  /** 파라미터 없음 — 아무것도 안 함 */
  | { readonly type: "none" }
  /** 판정 근거(목록 · me · 정착된 활성 ws)를 기다린다 — 전환·제거 0 */
  | { readonly type: "wait" }
  /** 전환 없이 파라미터만 제거 — 비UUID · 같은 ws · 비멤버 */
  | { readonly type: "strip" }
  /** 멤버이고 활성과 다름 — 1회 전환 후 파라미터 제거 */
  | { readonly type: "switch"; readonly workspaceId: string; readonly workspaceName: string };

export interface WorkspaceDeepLinkInput {
  readonly workspaceParam: string | null;
  readonly workspaces: readonly Pick<Workspace, "id" | "name">[] | undefined;
  readonly isWorkspaceListPending: boolean;
  readonly meId: string | undefined;
  readonly activeWorkspaceId: string | null;
}

/**
 * 알림 딥링크 `?workspace=<wid>` 판정 (pwa.md §5.5 표).
 *
 * ★활성 ws 가 목록 안의 값으로 정착하기 전에는 판정하지 않는다 — 자식(회의 상세)의 전환 effect 뒤
 *   같은 커밋에서 부모(panel-layout) self-heal 이 낡은 클로저로 `workspaces[0]` 을 덮어쓴다
 *   (scratchpad eval-spec3/deeplink-selfheal-race.cjs S2~S4).
 */
export function resolveWorkspaceDeepLink(input: WorkspaceDeepLinkInput): WorkspaceDeepLinkDecision {
  const { workspaceParam, workspaces, activeWorkspaceId } = input;
  if (workspaceParam === null) return { type: "none" };
  if (!UUID_RE.test(workspaceParam)) return { type: "strip" };
  if (workspaces === undefined) {
    // 목록 로딩 중이면 대기. 목록 조회 자체가 실패하면 멤버십을 확인할 수 없다 → 전환하지 않는다.
    return input.isWorkspaceListPending ? { type: "wait" } : { type: "strip" };
  }
  if (workspaces.length === 0) return { type: "strip" };
  if (!input.meId) return { type: "wait" };
  if (!activeWorkspaceId || !workspaces.some((workspace) => workspace.id === activeWorkspaceId)) {
    return { type: "wait" };
  }
  const targetId = workspaceParam.toLowerCase();
  if (targetId === activeWorkspaceId.toLowerCase()) return { type: "strip" };
  const target = workspaces.find((workspace) => workspace.id.toLowerCase() === targetId);
  if (!target) return { type: "strip" };
  return { type: "switch", workspaceId: target.id, workspaceName: target.name };
}
